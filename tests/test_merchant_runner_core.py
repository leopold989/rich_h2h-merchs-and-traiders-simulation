from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app


class RecordingPlatform:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def transport_factory(self, base_url: str) -> httpx.AsyncBaseTransport | None:
        if 'platform-rich-dev.local' not in base_url:
            return None
        return httpx.MockTransport(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        body: Any = None
        if request.content:
            if request.headers.get('content-type', '').startswith('application/json'):
                body = json.loads(request.content.decode('utf-8'))
            else:
                body = request.content.decode('utf-8', errors='replace')
        self.requests.append(
            {
                'method': request.method,
                'path': request.url.path,
                'url': str(request.url),
                'headers': dict(request.headers),
                'body': body,
            }
        )
        if request.method == 'POST' and request.url.path.endswith('/api/h2h/order'):
            assert isinstance(body, dict)
            payload = {
                'success': True,
                'data': {
                    'order_id': 'order-1',
                    'provider_order_id': 'provider-1',
                    'external_id': body['external_id'],
                    'merchant_id': body['merchant_id'],
                    'status': 'pending',
                    'sub_status': 'new',
                },
            }
            return httpx.Response(status_code=200, json=payload)
        if request.method == 'GET' and request.url.path.endswith('/api/h2h/order/order-1'):
            return httpx.Response(
                status_code=200,
                json={'success': True, 'data': {'order_id': 'order-1', 'status': 'pending', 'sub_status': 'polled'}},
            )
        return httpx.Response(status_code=404, json={'success': False, 'message': 'not found'})


def _rewrite_light_schedule(copied_light_profile: Path) -> None:
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['merchant_jobs'][0]['schedule']['start_delay_sec'] = 0
    data['merchant_jobs'][0]['schedule']['interval_sec'] = 1
    data['merchant_jobs'][0]['schedule']['requests_total'] = 1
    data['defaults']['poll_after_create']['delay_ms'] = 10
    data['defaults']['poll_after_create']['attempts'] = 1
    data['defaults']['poll_after_create']['interval_ms'] = 10
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _wait_until(predicate, timeout: float = 3.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('condition was not met before timeout')


def test_merchant_runner_creates_order_and_exposes_runtime_state(copied_light_profile: Path) -> None:
    _rewrite_light_schedule(copied_light_profile)
    platform = RecordingPlatform()
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_total'
            ]
            >= 1
            and bool(
                client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                    'orders_recent'
                ][0]['poll_history']
            )
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        assert state['merchant_runtime']['orders_total'] == 1
        order = state['merchant_runtime']['orders_recent'][0]
        assert order['create_ok'] is True
        assert order['order_id'] == 'order-1'
        assert order['status'] == 'pending'
        assert order['poll_history'][0]['sub_status'] == 'polled'

    create_calls = [item for item in platform.requests if item['method'] == 'POST' and item['path'].endswith('/api/h2h/order')]
    assert len(create_calls) == 1
    sent = create_calls[0]
    assert sent['body']['merchant_id'] == '8bc8a8d0-77e2-4ff5-9ff6-b9b74fd51a11'
    assert sent['body']['callback_url'] == 'https://sim.dev.rich.local/callbacks/merchants/merchant_light'
    assert 'access-token' in {key.lower() for key in sent['headers']}


def test_merchant_callback_receiver_updates_order_state(copied_light_profile: Path) -> None:
    _rewrite_light_schedule(copied_light_profile)
    platform = RecordingPlatform()
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_total'
            ]
            >= 1
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        order = state['merchant_runtime']['orders_recent'][0]
        callback = {
            'order_id': order['order_id'],
            'external_id': order['external_id'],
            'status': 'success',
            'sub_status': 'finished',
        }
        response = client.post(
            '/callbacks/merchants/merchant_light',
            headers={'Access-Token': 'merchant-light-token', 'Content-Type': 'application/json'},
            json=callback,
        )
        assert response.status_code == 200
        assert response.json()['success'] is True

        updated = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        order_after = updated['merchant_runtime']['orders_recent'][0]
        assert order_after['callbacks_received'] == 1
        assert order_after['status'] == 'success'
        assert order_after['sub_status'] == 'finished'


def test_merchant_callback_receiver_rejects_bad_token(copied_light_profile: Path) -> None:
    _rewrite_light_schedule(copied_light_profile)
    platform = RecordingPlatform()
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        response = client.post(
            '/callbacks/merchants/merchant_light',
            headers={'Access-Token': 'wrong-token', 'Content-Type': 'application/json'},
            json={'order_id': 'missing-order'},
        )
        assert response.status_code == 403


def test_hot_reload_recreates_completed_job_with_same_id(copied_light_profile: Path) -> None:
    _rewrite_light_schedule(copied_light_profile)
    platform = RecordingPlatform()
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_total'
            ]
            == 1
        )

        merchant_path = copied_light_profile.parent / 'merchant.json'
        data = json.loads(merchant_path.read_text(encoding='utf-8'))
        data['request_templates'][0]['request']['amount'] = 7777
        data['merchant_jobs'][0]['schedule']['start_delay_sec'] = 0
        data['merchant_jobs'][0]['schedule']['interval_sec'] = 1
        data['merchant_jobs'][0]['schedule']['requests_total'] = 1
        data['merchant_jobs'][0]['external_id']['pattern'] = 'reloaded-{seq}'
        merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        time.sleep(0.05)

        reload_response = client.post('/_sim/reload', headers={'X-Control-Token': 'light-write-token'})
        assert reload_response.status_code == 200
        assert reload_response.json()['status'] == 'ok'

        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_total'
            ]
            == 2
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        external_ids = {order['external_id'] for order in state['merchant_runtime']['orders_recent']}
        assert 'reloaded-2' in external_ids

    create_calls = [item for item in platform.requests if item['method'] == 'POST' and item['path'].endswith('/api/h2h/order')]
    assert len(create_calls) == 2
    assert create_calls[-1]['body']['amount'] == 7777
    assert create_calls[-1]['body']['external_id'] == 'reloaded-2'


def test_hot_reload_recreate_active_job_keeps_runtime_job_active(copied_light_profile: Path) -> None:
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['merchant_jobs'][0]['schedule']['start_delay_sec'] = 0
    data['merchant_jobs'][0]['schedule']['interval_sec'] = 30
    data['merchant_jobs'][0]['schedule']['requests_total'] = 5
    data['defaults']['poll_after_create']['delay_ms'] = 10
    data['defaults']['poll_after_create']['attempts'] = 1
    data['defaults']['poll_after_create']['interval_ms'] = 10
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    platform = RecordingPlatform()
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_total'
            ]
            == 1
        )

        reloaded = json.loads(merchant_path.read_text(encoding='utf-8'))
        reloaded['request_templates'][0]['request']['amount'] = 9100
        merchant_path.write_text(json.dumps(reloaded, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        time.sleep(0.05)

        reload_response = client.post('/_sim/reload', headers={'X-Control-Token': 'light-write-token'})
        assert reload_response.status_code == 200
        assert reload_response.json()['status'] == 'ok'

        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'jobs'
            ]['merchant_light_job']['active']
            is True
            and client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'jobs'
            ]['merchant_light_job']['finished_at']
            is None
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        job = state['merchant_runtime']['jobs']['merchant_light_job']
        assert job['active'] is True
        assert job['finished_at'] is None
