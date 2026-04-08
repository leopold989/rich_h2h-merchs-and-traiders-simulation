from __future__ import annotations

import json
from pathlib import Path

import pytest

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.exceptions import ConfigError


def test_light_profile_is_valid(copied_light_profile: Path) -> None:
    manager = ConfigManager(copied_light_profile)
    state = manager.get_state_snapshot()
    assert state['counts']['merchants'] == 1
    assert state['counts']['traders'] == 1


def test_medium_profile_is_valid(copied_medium_profile: Path) -> None:
    manager = ConfigManager(copied_medium_profile)
    state = manager.get_state_snapshot()
    assert state['counts']['request_templates'] >= 3
    assert state['counts']['traders'] >= 2


def test_unknown_template_id_fails(copied_light_profile: Path) -> None:
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['merchant_jobs'][0]['template_id'] = 'missing_template'
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    with pytest.raises(ConfigError, match='unknown template_id'):
        ConfigManager(copied_light_profile)


def test_payment_gateway_currency_conflict_fails(copied_light_profile: Path) -> None:
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['request_templates'][0]['request']['currency'] = 'RUB'
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    with pytest.raises(ConfigError, match='mutually exclusive'):
        ConfigManager(copied_light_profile)


def test_missing_fixture_fails(copied_medium_profile: Path) -> None:
    fixture_path = copied_medium_profile.parent / 'fixtures' / 'receipts' / 'dispute_halyk_001.pdf'
    fixture_path.unlink()

    with pytest.raises(ConfigError, match='missing receipt file'):
        ConfigManager(copied_medium_profile)


def test_inactive_referenced_response_profile_fails(copied_light_profile: Path) -> None:
    trader_path = copied_light_profile.parent / 'trader.json'
    data = json.loads(trader_path.read_text(encoding='utf-8'))
    data['response_profiles'][0]['active'] = False
    trader_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    with pytest.raises(ConfigError, match='inactive default_response_profile_id'):
        ConfigManager(copied_light_profile)


def test_safety_limits_can_block_overloaded_profile(copied_light_profile: Path) -> None:
    system_path = copied_light_profile
    merchant_path = copied_light_profile.parent / 'merchant.json'

    system = json.loads(system_path.read_text(encoding='utf-8'))
    system['safety'] = {
        'enabled': True,
        'mode': 'shared_dev',
        'max_active_jobs': 1,
        'max_total_inflight': 1,
        'max_requests_per_minute_estimate': 1,
    }
    system_path.write_text(json.dumps(system, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    merchant = json.loads(merchant_path.read_text(encoding='utf-8'))
    merchant['merchant_jobs'][0]['schedule']['interval_sec'] = 1
    merchant['merchant_jobs'][0]['schedule']['max_inflight'] = 2
    merchant_path.write_text(json.dumps(merchant, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    with pytest.raises(ConfigError, match='safety limit exceeded'):
        ConfigManager(copied_light_profile)


def test_heavy_profiles_are_valid(project_root: Path) -> None:
    shared_dev = project_root / 'examples' / 'heavy' / 'shared-dev' / 'system.json'
    dedicated = project_root / 'examples' / 'heavy' / 'dedicated' / 'system.json'
    assert ConfigManager(shared_dev).get_state_snapshot()['safety']['mode'] == 'shared_dev'
    assert ConfigManager(dedicated).get_state_snapshot()['safety']['mode'] == 'dedicated'
