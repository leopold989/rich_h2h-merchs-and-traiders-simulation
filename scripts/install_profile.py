#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from rich_h2h_simulator.devtools import list_available_profiles, prepare_profile_workspace
from rich_h2h_simulator.exceptions import ConfigError


def main() -> None:
    available_profiles = ', '.join(list_available_profiles())
    parser = argparse.ArgumentParser(description='Prepare a self-contained simulator workspace from examples/<profile>.')
    parser.add_argument('--profile', required=True, help=f'Profile name. Available: {available_profiles}')
    parser.add_argument('--workspace', required=True, help='Target directory for config/logs/fixtures workspace')
    parser.add_argument('--overwrite', action='store_true', help='Recreate workspace if it already exists')
    parser.add_argument('--no-copy-fixtures', action='store_true', help='Create empty fixtures directory instead of copying repo fixtures')
    parser.add_argument('--json', action='store_true', help='Print workspace summary as JSON')
    args = parser.parse_args()

    try:
        prepared = prepare_profile_workspace(
            profile=args.profile,
            workspace=args.workspace,
            overwrite=args.overwrite,
            copy_fixtures=not args.no_copy_fixtures,
        )
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if args.json:
        print(json.dumps(prepared.to_dict(), indent=2, ensure_ascii=False))
        return

    print(f'Workspace prepared: {prepared.root_dir}')
    print(f'  system.json:   {prepared.system_config_path}')
    print(f'  merchant.json: {prepared.merchant_config_path}')
    print(f'  trader.json:   {prepared.trader_config_path}')
    print(f'  logs dir:      {prepared.log_dir}')
    print(f'  fixtures dir:  {prepared.fixtures_dir}')
    print()
    print('Next steps:')
    print(f'  1) python scripts/validate_config.py --system-config {prepared.system_config_path}')
    print(f'  2) python scripts/run_profile.py --system-config {prepared.system_config_path}')
    print(f'  3) python scripts/http_smoke.py --system-config {prepared.system_config_path} --base-url http://127.0.0.1:8099')


if __name__ == '__main__':
    main()
