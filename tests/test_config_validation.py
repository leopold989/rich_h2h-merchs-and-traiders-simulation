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
