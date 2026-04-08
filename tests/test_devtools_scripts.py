from __future__ import annotations

import json
from pathlib import Path

import pytest

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.devtools import (
    build_trader_smoke_case,
    list_available_profiles,
    prepare_profile_workspace,
    read_last_lines,
    resolve_log_paths,
)
from rich_h2h_simulator.exceptions import ConfigError


def test_prepare_profile_workspace_creates_self_contained_layout(tmp_path: Path, project_root: Path) -> None:
    workspace = tmp_path / 'workspace-light'
    prepared = prepare_profile_workspace(profile='light', workspace=workspace, root=project_root)

    assert prepared.system_config_path.exists()
    assert prepared.merchant_config_path.exists()
    assert prepared.trader_config_path.exists()
    assert prepared.log_dir.exists()
    assert (prepared.fixtures_dir / 'receipts' / 'sbp_ok_001.png').exists()

    system = json.loads(prepared.system_config_path.read_text(encoding='utf-8'))
    assert system['paths']['merchant_config'] == './merchant.json'
    assert system['paths']['trader_config'] == './trader.json'
    assert system['paths']['fixtures_dir'] == '../fixtures'
    assert system['paths']['log_dir'] == '../logs'

    manager = ConfigManager(prepared.system_config_path)
    snapshot = manager.get_state_snapshot()
    assert snapshot['counts']['merchants'] == 1
    assert snapshot['counts']['traders'] == 1


def test_resolve_log_paths_and_read_last_lines(copied_light_profile: Path) -> None:
    manager = ConfigManager(copied_light_profile)
    paths = resolve_log_paths(copied_light_profile)
    assert set(paths) == {'system', 'merchant_outbound', 'merchant_callbacks', 'trader_inbound', 'trader_outbound'}

    system_log = paths['system']
    system_log.write_text('line-1\nline-2\nline-3\n', encoding='utf-8')
    assert read_last_lines(system_log, limit=2) == ['line-2', 'line-3']

    filtered = resolve_log_paths(copied_light_profile, channels=['system', 'trader_outbound'])
    assert set(filtered) == {'system', 'trader_outbound'}
    assert manager.bundle.system.logging.channels.system == 'system.log'


def test_build_trader_smoke_case_generates_valid_payload_for_medium(copied_medium_profile: Path) -> None:
    case = build_trader_smoke_case(copied_medium_profile)
    assert case['trader_alias'] == 'trader_sbp_pool'
    assert case['headers']['Access-Token'] == 'provider-sbp-token'
    assert case['api_root'].endswith('/traders/trader_sbp_pool/api/h2h')
    assert case['payload']['merchant_id'] == 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111'
    assert case['payload']['payment_gateway'] == 'sbp_rub'
    assert case['payload']['payment_detail_type'] == 'phone'
    assert case['payload']['amount'] >= 1000
    assert 'external_id' in case['payload']


def test_prepare_profile_workspace_refuses_overwrite_without_marker(tmp_path: Path, project_root: Path) -> None:
    dangerous = tmp_path / 'not-a-workspace'
    dangerous.mkdir()
    (dangerous / 'keep.txt').write_text('do not delete', encoding='utf-8')

    with pytest.raises(ConfigError, match='Refusing to overwrite'):
        prepare_profile_workspace(profile='light', workspace=dangerous, root=project_root, overwrite=True)

    assert (dangerous / 'keep.txt').read_text(encoding='utf-8') == 'do not delete'


def test_prepare_profile_workspace_can_overwrite_its_own_marker_workspace(tmp_path: Path, project_root: Path) -> None:
    workspace = tmp_path / 'workspace-light'
    prepare_profile_workspace(profile='light', workspace=workspace, root=project_root)
    (workspace / 'logs' / 'old.log').write_text('old', encoding='utf-8')

    prepared = prepare_profile_workspace(profile='light', workspace=workspace, root=project_root, overwrite=True)
    assert prepared.system_config_path.exists()
    assert not (workspace / 'logs' / 'old.log').exists()


def test_build_trader_smoke_case_intersects_rule_and_requisite_amount_ranges(copied_medium_profile: Path) -> None:
    trader_path = copied_medium_profile.parent / 'trader.json'
    trader = json.loads(trader_path.read_text(encoding='utf-8'))
    sbp_trader = next(item for item in trader['traders'] if item['alias'] == 'trader_sbp_pool')
    sbp_rule = next(item for item in sbp_trader['routing_rules'] if item['id'] == 'sbp_phone_low_amount')
    sbp_rule['match']['amount'] = {'gte': 1000}
    req = next(item for item in sbp_trader['requisites'] if item['id'] == 'sbp_phone_01')
    req['amount_range'] = {'min': 5000, 'max': 6000}
    trader_path.write_text(json.dumps(trader, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    case = build_trader_smoke_case(copied_medium_profile)
    assert 5000 <= case['payload']['amount'] <= 6000


def test_list_available_profiles_includes_nested_heavy_variants(project_root: Path) -> None:
    profiles = set(list_available_profiles(root=project_root))
    assert {'light', 'medium', 'heavy', 'heavy/shared-dev', 'heavy/dedicated'}.issubset(profiles)
