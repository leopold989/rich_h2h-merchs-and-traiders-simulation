from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app


def test_health_and_control_api(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        health = client.get('/health')
        assert health.status_code == 200
        assert health.json()['status'] in {'ok', 'degraded'}

        forbidden = client.get('/_sim/state')
        assert forbidden.status_code == 401

        ok = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'})
        assert ok.status_code == 200
        assert ok.json()['counts']['merchants'] == 1

        masked = client.get('/_sim/config', headers={'X-Control-Token': 'light-read-token'})
        body = masked.json()
        assert body['merchant']['merchants'][0]['access_token'] == '***masked***'
        assert body['trader']['traders'][0]['auth']['access_token'] == '***masked***'

        reload_result = client.post('/_sim/reload', headers={'X-Control-Token': 'light-write-token'})
        assert reload_result.status_code == 200
        assert reload_result.json()['status'] == 'ok'


def test_read_token_cannot_reload(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        response = client.post('/_sim/reload', headers={'X-Control-Token': 'light-read-token'})
        assert response.status_code == 403
