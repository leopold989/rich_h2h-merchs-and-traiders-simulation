#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from rich_h2h_simulator.devtools import follow_logs, read_last_lines, resolve_log_paths
from rich_h2h_simulator.exceptions import ConfigError


def main() -> None:
    parser = argparse.ArgumentParser(description='Read simulator JSONL logs from a given system.json')
    parser.add_argument('--system-config', default='config/system.json', help='Path to system.json')
    parser.add_argument('--channels', nargs='*', help='Optional list of channel names')
    parser.add_argument('--lines', type=int, default=20, help='How many trailing lines to print per file')
    parser.add_argument('--follow', action='store_true', help='Continue following files after printing the tail')
    parser.add_argument('--sleep-sec', type=float, default=0.5, help='Polling interval for --follow mode')
    args = parser.parse_args()
    try:
        paths = resolve_log_paths(args.system_config, channels=args.channels)
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

    if args.follow:
        follow_logs(paths, lines=args.lines, sleep_sec=args.sleep_sec)
        return

    for channel, path in paths.items():
        print(f'===== {channel}: {path} =====')
        lines = read_last_lines(path, limit=args.lines)
        if not lines:
            print('<empty>')
        else:
            for line in lines:
                print(line)


if __name__ == '__main__':
    main()
