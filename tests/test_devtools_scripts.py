from __future__ import annotations

import json
from pathlib import Path

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.devtools import build_trader_smoke_case, prepare_profile_workspace, read_last_lines, resolve_log_paths


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
