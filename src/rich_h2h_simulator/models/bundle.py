from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich_h2h_simulator.models.merchant import MerchantConfig
from rich_h2h_simulator.models.system import SystemConfig
from rich_h2h_simulator.models.trader import TraderConfig


@dataclass(slots=True)
class ConfigBundle:
    system: SystemConfig
    merchant: MerchantConfig
    trader: TraderConfig
    system_path: Path
    merchant_path: Path
    trader_path: Path
