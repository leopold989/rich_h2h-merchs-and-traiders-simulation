from __future__ import annotations

from pathlib import Path

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.logging_setup import log_event, setup_logging


def test_logging_initializes_all_channels(copied_light_profile: Path) -> None:
    manager = ConfigManager(copied_light_profile)
    log_dir = (copied_light_profile.parent / 'logs').resolve()
    registry = setup_logging(manager.bundle.system.logging, log_dir)
    logger = registry.get('system')
    log_event(logger, 'test_event', {'sample': True})
    for handler in logger.handlers:
        handler.flush()

    expected = {
        'system.log',
        'merchant_outbound.log',
        'merchant_callbacks.log',
        'trader_inbound.log',
        'trader_outbound.log',
    }
    assert expected.issubset({item.name for item in log_dir.iterdir()})
    system_log = log_dir / 'system.log'
    content = system_log.read_text(encoding='utf-8')
    assert 'test_event' in content
