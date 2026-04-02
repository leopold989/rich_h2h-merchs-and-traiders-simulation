from __future__ import annotations

import json
import time
from pathlib import Path

from rich_h2h_simulator.config_loader import ConfigManager


def test_reload_keeps_previous_bundle_on_invalid_change(copied_light_profile: Path) -> None:
    manager = ConfigManager(copied_light_profile)
    before = manager.get_state_snapshot()

    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['merchant_jobs'][0]['template_id'] = 'invalid-template'
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    time.sleep(0.05)

    result = manager.reload(force=True)
    assert result.success is False
    assert 'unknown template_id' in result.message
    after = manager.get_state_snapshot()
    assert after['counts'] == before['counts']
    assert manager.bundle.merchant.merchant_jobs[0].template_id == 'light_rub_sbp'


def test_reload_applies_valid_change(copied_light_profile: Path) -> None:
    manager = ConfigManager(copied_light_profile)

    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['request_templates'][0]['description'] = 'updated description'
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    time.sleep(0.05)

    result = manager.reload(force=True)
    assert result.success is True
    assert manager.bundle.merchant.request_templates[0].description == 'updated description'
