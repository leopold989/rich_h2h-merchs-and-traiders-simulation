#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from rich_h2h_simulator.app_factory import create_app
from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.devtools import list_available_profiles, resolve_system_config


def main() -> None:
    available_profiles = ', '.join(list_available_profiles())
    parser = argparse.ArgumentParser(description='Run simulator using a selected profile, workspace or explicit system.json')
    parser.add_argument('--profile', help=f'Use examples/<profile>/system.json. Available: {available_profiles}')
    parser.add_argument('--workspace', help='Use <workspace>/config/system.json')
    parser.add_argument('--system-config', help='Explicit path to system.json')
    parser.add_argument('--host', help='Override listen host')
    parser.add_argument('--port', type=int, help='Override listen port')
    args = parser.parse_args()

    system_path = resolve_system_config(profile=args.profile, system_config=args.system_config, workspace=args.workspace)
    os.environ['SIM_SYSTEM_CONFIG'] = str(system_path)
    manager = ConfigManager(system_path)
    config = manager.bundle.system.service
    app = create_app(system_path)
    uvicorn.run(app, host=args.host or config.listen_host, port=args.port or config.listen_port)


if __name__ == '__main__':
    main()
