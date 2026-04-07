#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from rich_h2h_simulator.devtools import SmokeCheckError, run_http_smoke


def main() -> None:
    parser = argparse.ArgumentParser(description='Run HTTP smoke checks against a running simulator instance')
    parser.add_argument('--system-config', default='config/system.json', help='Path to system.json used by the running app')
    parser.add_argument('--base-url', default='http://127.0.0.1:8099', help='Base URL of the running simulator')
    parser.add_argument('--timeout-sec', type=float, default=10.0)
    args = parser.parse_args()

    try:
        summary = run_http_smoke(args.base_url, args.system_config, timeout_sec=args.timeout_sec)
    except SmokeCheckError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # noqa: BLE001
        print(f'Unexpected smoke error: {exc}', file=sys.stderr)
        raise SystemExit(1) from exc

    print(json.dumps(summary.results, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
