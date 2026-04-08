from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import ValidationError

from rich_h2h_simulator.config_validation import summarize_safety, validate_bundle
from rich_h2h_simulator.exceptions import ConfigError
from rich_h2h_simulator.models.bundle import ConfigBundle
from rich_h2h_simulator.models.merchant import MerchantConfig
from rich_h2h_simulator.models.system import SystemConfig
from rich_h2h_simulator.models.trader import TraderConfig


@dataclass(slots=True)
class ReloadResult:
    success: bool
    changed: bool
    message: str
    attempted_at: datetime


class ConfigManager:
    def __init__(self, system_path: str | Path) -> None:
        self._lock = Lock()
        self.system_path = Path(system_path).resolve()
        self._bundle: ConfigBundle | None = None
        self._public_bundle: dict[str, Any] | None = None
        self._mtimes: dict[str, float] = {}
        self._digests: dict[str, str] = {}
        self.app_started_at = datetime.now(UTC)
        self.last_reload_attempt_at: datetime | None = None
        self.last_reload_success_at: datetime | None = None
        self.last_reload_error: str | None = None
        self.reload_count = 0
        self.failed_reload_count = 0
        self.last_reload_changed = False
        self.load_initial()

    @property
    def bundle(self) -> ConfigBundle:
        assert self._bundle is not None
        return self._bundle

    @property
    def public_bundle(self) -> dict[str, Any]:
        assert self._public_bundle is not None
        return self._public_bundle

    def load_initial(self) -> None:
        bundle = self._load_bundle()
        self._apply(bundle)
        now = datetime.now(UTC)
        self.last_reload_attempt_at = now
        self.last_reload_success_at = now
        self.last_reload_error = None
        self.reload_count = 1
        self.last_reload_changed = True

    def reload(self, *, force: bool = False) -> ReloadResult:
        attempted_at = datetime.now(UTC)
        self.last_reload_attempt_at = attempted_at
        changed = self._has_changes() if not force else True
        if not changed and self._bundle is not None:
            return ReloadResult(True, False, 'No config changes detected', attempted_at)
        try:
            bundle = self._load_bundle()
        except Exception as exc:  # noqa: BLE001
            self.failed_reload_count += 1
            self.last_reload_error = str(exc)
            self.last_reload_changed = False
            return ReloadResult(False, changed, str(exc), attempted_at)
        self._apply(bundle)
        self.reload_count += 1
        self.last_reload_success_at = attempted_at
        self.last_reload_error = None
        self.last_reload_changed = changed
        return ReloadResult(True, changed, 'Configuration reloaded', attempted_at)

    def get_state_snapshot(self) -> dict[str, Any]:
        bundle = self.bundle
        return {
            'app_started_at': self.app_started_at.isoformat(),
            'last_reload_attempt_at': self._iso(self.last_reload_attempt_at),
            'last_reload_success_at': self._iso(self.last_reload_success_at),
            'last_reload_error': self.last_reload_error,
            'reload_count': self.reload_count,
            'failed_reload_count': self.failed_reload_count,
            'last_reload_changed': self.last_reload_changed,
            'system_config_path': str(bundle.system_path),
            'merchant_config_path': str(bundle.merchant_path),
            'trader_config_path': str(bundle.trader_path),
            'digests': self._digests.copy(),
            'counts': {
                'request_templates': len(bundle.merchant.request_templates),
                'merchants': len(bundle.merchant.merchants),
                'merchant_jobs': len(bundle.merchant.merchant_jobs),
                'response_profiles': len(bundle.trader.response_profiles),
                'traders': len(bundle.trader.traders),
            },
            'safety': summarize_safety(bundle),
        }

    def _apply(self, bundle: ConfigBundle) -> None:
        with self._lock:
            self._bundle = bundle
            self._mtimes = self._collect_mtimes(bundle)
            self._digests = self._collect_digests(bundle)
            self._public_bundle = self._make_public_bundle(bundle)

    def _load_bundle(self) -> ConfigBundle:
        system_data = self._load_json(self.system_path)
        try:
            system = SystemConfig.model_validate(system_data)
        except ValidationError as exc:
            raise ConfigError(self._format_validation_error('system.json', exc)) from exc

        root = self.system_path.parent
        merchant_path = self._resolve(root, system.paths.merchant_config)
        trader_path = self._resolve(root, system.paths.trader_config)

        merchant_data = self._load_json(merchant_path)
        trader_data = self._load_json(trader_path)
        try:
            merchant = MerchantConfig.model_validate(merchant_data)
        except ValidationError as exc:
            raise ConfigError(self._format_validation_error(str(merchant_path.name), exc)) from exc
        try:
            trader = TraderConfig.model_validate(trader_data)
        except ValidationError as exc:
            raise ConfigError(self._format_validation_error(str(trader_path.name), exc)) from exc
        bundle = ConfigBundle(
            system=system,
            merchant=merchant,
            trader=trader,
            system_path=self.system_path,
            merchant_path=merchant_path,
            trader_path=trader_path,
        )
        validate_bundle(bundle)
        return bundle

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ConfigError(f'Config file does not exist: {path}')
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise ConfigError(f'Invalid JSON in {path}: {exc}') from exc

    def _has_changes(self) -> bool:
        bundle = self.bundle
        current = self._collect_mtimes(bundle)
        for name, value in current.items():
            if self._mtimes.get(name) != value:
                return True
        return False

    def _collect_mtimes(self, bundle: ConfigBundle) -> dict[str, float]:
        return {
            'system': bundle.system_path.stat().st_mtime,
            'merchant': bundle.merchant_path.stat().st_mtime,
            'trader': bundle.trader_path.stat().st_mtime,
        }

    def _collect_digests(self, bundle: ConfigBundle) -> dict[str, str]:
        return {
            'system': self._sha256(bundle.system_path),
            'merchant': self._sha256(bundle.merchant_path),
            'trader': self._sha256(bundle.trader_path),
        }

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(path.read_bytes())
        return digest.hexdigest()

    def _make_public_bundle(self, bundle: ConfigBundle) -> dict[str, Any]:
        data = {
            'system': bundle.system.model_dump(mode='json'),
            'merchant': bundle.merchant.model_dump(mode='json'),
            'trader': bundle.trader.model_dump(mode='json'),
        }
        mask_headers = {item.lower() for item in bundle.system.logging.payload_limits.mask_headers}
        return self._mask(data, mask_headers)

    def _mask(self, value: Any, mask_headers: set[str], parent_key: str | None = None) -> Any:
        secret_keys = {
            'access_token',
            'read_only_token',
            'write_token',
        }
        if isinstance(value, dict):
            masked: dict[str, Any] = {}
            for key, item in value.items():
                lower_key = key.lower()
                if lower_key in secret_keys:
                    masked[key] = '***masked***'
                    continue
                if parent_key in {'headers', 'default_headers'} and lower_key in mask_headers:
                    masked[key] = '***masked***'
                    continue
                masked[key] = self._mask(item, mask_headers, lower_key)
            return masked
        if isinstance(value, list):
            return [self._mask(item, mask_headers, parent_key) for item in value]
        return value

    def _resolve(self, base: Path, raw: str) -> Path:
        candidate = Path(raw)
        if candidate.is_absolute():
            return candidate
        return (base / candidate).resolve()

    def _format_validation_error(self, name: str, exc: ValidationError) -> str:
        parts: list[str] = []
        for error in exc.errors():
            loc = '.'.join(str(item) for item in error['loc'])
            parts.append(f'{name}: {loc}: {error["msg"]}')
        return '\n'.join(parts)

    def _iso(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()
