from __future__ import annotations

from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app
from rich_h2h_simulator.devtools import execute_http_smoke


def test_light_profile_http_smoke_passes(copied_light_profile):
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        result = execute_http_smoke(client, copied_light_profile)
    assert result['health']['status'] == 'ok'
    assert result['control_api']['reload']['status'] == 'ok'
    assert result['trader']['create']['success'] is True
    assert result['trader']['cancel']['success'] is True
    assert result['trader']['smoke_case']['trader_alias'] == 'trader_light'


def test_medium_profile_http_smoke_passes(copied_medium_profile):
    app = create_app(copied_medium_profile)
    with TestClient(app) as client:
        result = execute_http_smoke(client, copied_medium_profile)
    assert result['health']['status'] == 'ok'
    assert result['control_api']['reload']['status'] == 'ok'
    assert result['trader']['create']['success'] is True
    assert result['trader']['show_by_id']['data']['external_id'] == result['trader']['smoke_case']['payload']['external_id']
    assert result['trader']['cancel']['success'] is True
    assert result['trader']['smoke_case']['trader_alias'] == 'trader_sbp_pool'
