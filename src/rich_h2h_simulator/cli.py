from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rich_h2h_simulator.config_loader import ConfigManager
from rich_h2h_simulator.exceptions import ConfigError


def main() -> None:
    parser = argparse.ArgumentParser(description='Validate simulator JSON configs')
    parser.add_argument('--system-config', default='config/system.json', help='Path to system.json')
    parser.add_argument('--dump-state', action='store_true', help='Print state snapshot after validation')
    args = parser.parse_args()
    try:
        manager = ConfigManager(Path(args.system_config))
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # noqa: BLE001
        print(f'Unexpected error: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc
    print(f'Config validation OK: {Path(args.system_config).resolve()}')
    if args.dump_state:
        print(json.dumps(manager.get_state_snapshot(), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
