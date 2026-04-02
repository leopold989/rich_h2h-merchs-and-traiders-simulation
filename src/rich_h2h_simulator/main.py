from __future__ import annotations

import os

import uvicorn

from rich_h2h_simulator.app_factory import create_app
from rich_h2h_simulator.config_loader import ConfigManager


def run() -> None:
    system_path = os.environ.get('SIM_SYSTEM_CONFIG', 'config/system.json')
    manager = ConfigManager(system_path)
    config = manager.bundle.system.service
    app = create_app(system_path)
    uvicorn.run(app, host=config.listen_host, port=config.listen_port)


if __name__ == '__main__':
    run()
