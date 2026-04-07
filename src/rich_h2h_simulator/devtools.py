from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import httpx

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.exceptions import ConfigError, SimulatorError
from rich_h2h_simulator.models.bundle import ConfigBundle
from rich_h2h_simulator.models.trader import RequisiteConfig, RoutingRuleConfig, TraderConfigEntry

PROFILE_NAMES = ('light', 'medium', 'heavy')


class SmokeCheckError(SimulatorError):
    """Raised when the HTTP smoke plan fails."""


@dataclass(slots=True)
class PreparedWorkspace:
    profile: str
    root_dir: Path
    config_dir: Path
    log_dir: Path
    fixtures_dir: Path
    system_config_path: Path
    merchant_config_path: Path
    trader_config_path: Path

    def to_dict(self) -> dict[str, str]:
        return {
            'profile': self.profile,
            'root_dir': str(self.root_dir),
            'config_dir': str(self.config_dir),
            'log_dir': str(self.log_dir),
            'fixtures_dir': str(self.fixtures_dir),
            'system_config_path': str(self.system_config_path),
            'merchant_config_path': str(self.merchant_config_path),
            'trader_config_path': str(self.trader_config_path),
        }


class SyncHttpClient(Protocol):
    def get(self, url: str, **kwargs: Any): ...

    def post(self, url: str, **kwargs: Any): ...

    def patch(self, url: str, **kwargs: Any): ...


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_profile_dir(profile: str, *, root: Path | None = None) -> Path:
    if profile not in PROFILE_NAMES:
        allowed = ', '.join(PROFILE_NAMES)
        raise ConfigError(f'Unknown profile: {profile}. Expected one of: {allowed}')
    base_root = (root or project_root()).resolve()
    profile_dir = base_root / 'examples' / profile
    if not profile_dir.exists():
        raise ConfigError(f'Profile directory does not exist: {profile_dir}')
    return profile_dir


def resolve_system_config(
    *,
    profile: str | None = None,
    system_config: str | Path | None = None,
    workspace: str | Path | None = None,
    root: Path | None = None,
) -> Path:
    if system_config is not None:
        return Path(system_config).resolve()
    if workspace is not None:
        candidate = Path(workspace).resolve() / 'config' / 'system.json'
        return candidate
    if profile is not None:
        return resolve_profile_dir(profile, root=root) / 'system.json'
    return (root or project_root()).resolve() / 'config' / 'system.json'


def prepare_profile_workspace(
    *,
    profile: str,
    workspace: str | Path,
    root: Path | None = None,
    overwrite: bool = False,
    copy_fixtures: bool = True,
) -> PreparedWorkspace:
    repo_root = (root or project_root()).resolve()
    profile_dir = resolve_profile_dir(profile, root=repo_root)
    workspace_dir = Path(workspace).resolve()
    config_dir = workspace_dir / 'config'
    log_dir = workspace_dir / 'logs'
    fixtures_dir = workspace_dir / 'fixtures'

    if workspace_dir.exists() and any(workspace_dir.iterdir()) and not overwrite:
        raise ConfigError(
            f'Workspace is not empty: {workspace_dir}. Use --overwrite or choose another path.'
        )

    if overwrite and workspace_dir.exists():
        shutil.rmtree(workspace_dir)

    config_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    if copy_fixtures:
        shutil.copytree(repo_root / 'fixtures', fixtures_dir, dirs_exist_ok=True)
    else:
        fixtures_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(profile_dir / 'merchant.json', config_dir / 'merchant.json')
    shutil.copy2(profile_dir / 'trader.json', config_dir / 'trader.json')

    system_path = config_dir / 'system.json'
    system = json.loads((profile_dir / 'system.json').read_text(encoding='utf-8'))
    system['paths']['merchant_config'] = './merchant.json'
    system['paths']['trader_config'] = './trader.json'
    system['paths']['fixtures_dir'] = '../fixtures'
    system['paths']['log_dir'] = '../logs'
    system_path.write_text(json.dumps(system, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    return PreparedWorkspace(
        profile=profile,
        root_dir=workspace_dir,
        config_dir=config_dir,
        log_dir=log_dir,
        fixtures_dir=fixtures_dir,
        system_config_path=system_path,
        merchant_config_path=config_dir / 'merchant.json',
        trader_config_path=config_dir / 'trader.json',
    )


def resolve_log_paths(system_config_path: str | Path, channels: list[str] | None = None) -> dict[str, Path]:
    manager = ConfigManager(system_config_path)
    bundle = manager.bundle
    log_dir = _resolve(bundle.system_path.parent, bundle.system.paths.log_dir)
    available = bundle.system.logging.channels.model_dump(mode='json')
    if channels is None:
        selected = available
    else:
        selected = {}
        for channel in channels:
            if channel not in available:
                raise ConfigError(f'Unknown log channel: {channel}')
            selected[channel] = available[channel]
    return {name: (log_dir / filename).resolve() for name, filename in selected.items()}


def read_last_lines(path: str | Path, limit: int = 20) -> list[str]:
    if limit <= 0:
        raise ValueError('limit must be positive')
    file_path = Path(path)
    if not file_path.exists():
        return []
    lines = file_path.read_text(encoding='utf-8', errors='replace').splitlines()
    return lines[-limit:]


def follow_logs(paths: dict[str, Path], *, lines: int = 20, sleep_sec: float = 0.5) -> None:
    for channel, path in paths.items():
        print(f'===== {channel}: {path} =====')
        for line in read_last_lines(path, limit=lines):
            print(line)
    offsets = {path: path.stat().st_size if path.exists() else 0 for path in paths.values()}
    try:
        while True:
            time.sleep(sleep_sec)
            for channel, path in paths.items():
                if not path.exists():
                    continue
                size = path.stat().st_size
                if size < offsets[path]:
                    offsets[path] = 0
                if size == offsets[path]:
                    continue
                with path.open('r', encoding='utf-8', errors='replace') as handle:
                    handle.seek(offsets[path])
                    chunk = handle.read()
                    offsets[path] = handle.tell()
                if chunk:
                    for line in chunk.splitlines():
                        print(f'[{channel}] {line}')
    except KeyboardInterrupt:
        return


def build_trader_smoke_case(system_config_path: str | Path) -> dict[str, Any]:
    manager = ConfigManager(system_config_path)
    bundle = manager.bundle
    trader = _pick_smoke_trader(bundle)
    rule = _pick_smoke_rule(trader)
    requisite = _pick_smoke_requisite(trader, rule)
    amount = _pick_amount(rule, requisite)
    payment_gateway = rule.match.payment_gateway or requisite.payment_gateway
    payment_detail_type = rule.match.payment_detail_type or requisite.detail_type
    transgran = _pick_transgran(rule, requisite)
    external_id = f'smoke-{trader.alias}-{uuid4().hex[:12]}'
    api_root = f"{trader.base_path.rstrip('/')}{bundle.trader.defaults.api_prefix}"
    payload: dict[str, Any] = {
        'external_id': external_id,
        'amount': amount,
        'merchant_id': str(trader.auth.merchant_id),
        'payment_gateway': payment_gateway,
    }
    if payment_detail_type:
        payload['payment_detail_type'] = payment_detail_type
    if transgran is not None:
        payload['transgran'] = transgran
    return {
        'trader_alias': trader.alias,
        'headers': {'Access-Token': trader.auth.access_token},
        'api_root': api_root,
        'payload': payload,
        'control_prefix': bundle.system.control_api.prefix,
        'read_token': bundle.system.control_api.read_only_token,
        'write_token': bundle.system.control_api.write_token,
        'system_config_path': str(manager.system_path),
    }


def execute_http_smoke(client: SyncHttpClient, system_config_path: str | Path) -> dict[str, Any]:
    manager = ConfigManager(system_config_path)
    bundle = manager.bundle
    control_prefix = bundle.system.control_api.prefix
    read_token = bundle.system.control_api.read_only_token
    write_token = bundle.system.control_api.write_token
    smoke_case = build_trader_smoke_case(system_config_path)

    results: dict[str, Any] = {
        'system_config_path': str(manager.system_path),
        'health': None,
        'control_api': {},
        'trader': {},
    }

    health = client.get('/health')
    _expect_status(health, 200, 'GET /health')
    health_json = health.json()
    if health_json.get('status') not in {'ok', 'degraded'}:
        raise SmokeCheckError(f"Unexpected health payload: {health_json}")
    results['health'] = health_json

    state = client.get(f'{control_prefix}/state', headers={'X-Control-Token': read_token})
    _expect_status(state, 200, 'GET state')
    state_json = state.json()
    if 'merchant_runtime' not in state_json or 'trader_runtime' not in state_json:
        raise SmokeCheckError('State payload does not contain merchant_runtime/trader_runtime')
    results['control_api']['state'] = state_json

    config = client.get(f'{control_prefix}/config', headers={'X-Control-Token': read_token})
    _expect_status(config, 200, 'GET config')
    config_json = config.json()
    if config_json['system']['control_api']['read_only_token'] != '***masked***':
        raise SmokeCheckError('Public config does not mask read_only_token')
    results['control_api']['config'] = config_json

    reload_response = client.post(f'{control_prefix}/reload', headers={'X-Control-Token': write_token})
    _expect_status(reload_response, 200, 'POST reload')
    reload_json = reload_response.json()
    if reload_json.get('status') != 'ok':
        raise SmokeCheckError(f"Reload failed: {reload_json}")
    results['control_api']['reload'] = reload_json

    create = client.post(
        f"{smoke_case['api_root']}/order",
        headers=smoke_case['headers'],
        json=smoke_case['payload'],
    )
    _expect_status(create, 200, 'POST trader create')
    create_json = create.json()
    if create_json.get('success') is not True:
        raise SmokeCheckError(f"Trader create failed: {create_json}")
    order_id = create_json['data']['order_id']
    results['trader']['create'] = create_json

    show_by_id = client.get(f"{smoke_case['api_root']}/order/{order_id}", headers=smoke_case['headers'])
    _expect_status(show_by_id, 200, 'GET trader by order_id')
    show_by_id_json = show_by_id.json()
    if show_by_id_json.get('data', {}).get('external_id') != smoke_case['payload']['external_id']:
        raise SmokeCheckError(f"Unexpected trader by-id payload: {show_by_id_json}")
    results['trader']['show_by_id'] = show_by_id_json

    merchant_id = smoke_case['payload']['merchant_id']
    external_id = smoke_case['payload']['external_id']
    show_by_external = client.get(
        f"{smoke_case['api_root']}/order/{merchant_id}/{external_id}",
        headers=smoke_case['headers'],
    )
    _expect_status(show_by_external, 200, 'GET trader by merchant_id/external_id')
    show_by_external_json = show_by_external.json()
    if show_by_external_json.get('data', {}).get('order_id') != order_id:
        raise SmokeCheckError(f"Unexpected trader by-external payload: {show_by_external_json}")
    results['trader']['show_by_external'] = show_by_external_json

    cancel = client.patch(f"{smoke_case['api_root']}/order/{order_id}/cancel", headers=smoke_case['headers'])
    _expect_status(cancel, 200, 'PATCH trader cancel')
    cancel_json = cancel.json()
    if cancel_json.get('success') is not True:
        raise SmokeCheckError(f"Trader cancel failed: {cancel_json}")
    results['trader']['cancel'] = cancel_json
    results['trader']['smoke_case'] = smoke_case
    return results


@dataclass(slots=True)
class HttpSmokeSummary:
    success: bool
    results: dict[str, Any]


def run_http_smoke(base_url: str, system_config_path: str | Path, *, timeout_sec: float = 10.0) -> HttpSmokeSummary:
    transport = httpx.HTTPTransport(retries=0)
    with httpx.Client(base_url=base_url, timeout=timeout_sec, verify=False, transport=transport) as client:
        results = execute_http_smoke(client, system_config_path)
    return HttpSmokeSummary(success=True, results=results)


def _pick_smoke_trader(bundle: ConfigBundle) -> TraderConfigEntry:
    for trader in bundle.trader.traders:
        if trader.active:
            return trader
    raise SmokeCheckError('No active traders configured for smoke plan')


def _pick_smoke_rule(trader: TraderConfigEntry) -> RoutingRuleConfig:
    for rule in trader.routing_rules:
        if rule.active:
            return rule
    raise SmokeCheckError(f'Trader {trader.alias} does not have an active routing rule')


def _pick_smoke_requisite(trader: TraderConfigEntry, rule: RoutingRuleConfig) -> RequisiteConfig:
    if rule.requisite_pool:
        pool = {item.id: item for item in trader.requisites if item.active}
        for requisite_id in rule.requisite_pool:
            requisite = pool.get(requisite_id)
            if requisite is not None:
                return requisite
    for requisite in trader.requisites:
        if requisite.active:
            return requisite
    raise SmokeCheckError(f'Trader {trader.alias} does not have an active requisite')


def _pick_amount(rule: RoutingRuleConfig, requisite: RequisiteConfig) -> int:
    amount = rule.match.amount
    if amount is not None:
        lower = amount.gte if amount.gte is not None else amount.gt + 1 if amount.gt is not None else None
        upper = amount.lte if amount.lte is not None else amount.lt - 1 if amount.lt is not None else None
        if lower is not None and upper is not None:
            return max(lower, min(upper, (lower + upper) // 2))
        if lower is not None:
            return lower
        if upper is not None:
            return upper
    return max(requisite.amount_range.min, min(requisite.amount_range.max, requisite.amount_range.min + 1000))


def _pick_transgran(rule: RoutingRuleConfig, requisite: RequisiteConfig) -> bool | None:
    if rule.match.transgran is not None:
        return rule.match.transgran
    if rule.match.is_transgran is not None:
        return rule.match.is_transgran
    return requisite.is_transgran


def _resolve(base: Path, raw: str) -> Path:
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    return (base / candidate).resolve()


def _expect_status(response: Any, expected: int, label: str) -> None:
    if response.status_code != expected:
        body: Any
        try:
            body = response.json()
        except Exception:  # noqa: BLE001
            body = getattr(response, 'text', '<unavailable>')
        raise SmokeCheckError(f'{label} returned status {response.status_code}, expected {expected}: {body}')
