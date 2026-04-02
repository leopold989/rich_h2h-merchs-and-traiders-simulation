from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich_h2h_simulator.models.merchant import MerchantConfig
from rich_h2h_simulator.models.system import SystemConfig
from rich_h2h_simulator.models.trader import TraderConfig


SCHEMAS = {
    'system.schema.json': SystemConfig,
    'merchant.schema.json': MerchantConfig,
    'trader.schema.json': TraderConfig,
}


def main() -> None:
    parser = argparse.ArgumentParser(description='Export JSON schemas for simulator configs')
    parser.add_argument('--output-dir', default='schemas')
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in SCHEMAS.items():
        path = output_dir / filename
        path.write_text(json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'Wrote {path}')


if __name__ == '__main__':
    main()
