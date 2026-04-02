import sys

import json
import shutil
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


@pytest.fixture()
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_profile(project_root: Path, profile: str, tmp_path: Path) -> Path:
    example_dir = project_root / 'examples' / profile
    for item in example_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, tmp_path / item.name)
    fixtures_src = project_root / 'fixtures'
    shutil.copytree(fixtures_src, tmp_path / 'fixtures')
    (tmp_path / 'logs').mkdir()
    system_path = tmp_path / 'system.json'
    system = json.loads(system_path.read_text(encoding='utf-8'))
    system['paths']['merchant_config'] = './merchant.json'
    system['paths']['trader_config'] = './trader.json'
    system['paths']['fixtures_dir'] = './fixtures'
    system['paths']['log_dir'] = './logs'
    system_path.write_text(json.dumps(system, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return system_path


@pytest.fixture()
def copied_light_profile(tmp_path: Path, project_root: Path) -> Path:
    return _copy_profile(project_root, 'light', tmp_path)


@pytest.fixture()
def copied_medium_profile(tmp_path: Path, project_root: Path) -> Path:
    return _copy_profile(project_root, 'medium', tmp_path)
