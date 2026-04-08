from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app


class ActionPlatform:
    def __init__(self, action_type: str) -> None:
        self.action_type = action_type
        self.requests: list[dict[str, Any]] = []
        self.expected_path = {
            'cancel': '/api/h2h/order/order-1/cancel',
            'confirm_client': '/api/h2h/order/order-1/confirm-client',
            'add_receipt': '/api/h2h/order/order-1/add-receipt',
            'dispute': '/api/h2h/order/order-1/dispute',
            'finish': '/api/h2h/order/order-1/finish',
        }[action_type]

    def transport_factory(self, base_url: str) -> httpx.AsyncBaseTransport | None:
        if 'platform-rich-dev.local' not in base_url:
            return None
        return httpx.MockTransport(self._handler)

    def _handler(self, request: httpx.Request) -> httpx.Response:
        body: Any = None
        raw_body = request.content.decode('utf-8', errors='replace') if request.content else ''
        if request.headers.get('content-type', '').startswith('application/json') and request.content:
            body = json.loads(request.content.decode('utf-8'))
        elif request.content:
            body = raw_body
        record = {'method': request.method, 'path': request.url.path, 'headers': dict(request.headers), 'body': body}
        self.requests.append(record)
        if request.method == 'POST' and request.url.path.endswith('/api/h2h/order'):
            assert isinstance(body, dict)
            return httpx.Response(
                200,
                json={
                    'success': True,
                    'data': {
                        'order_id': 'order-1',
                        'external_id': body['external_id'],
                        'merchant_id': body['merchant_id'],
                        'status': 'pending',
                        'sub_status': 'created',
                    },
                },
            )
        if request.method == 'GET' and (
            request.url.path.endswith('/api/h2h/order/order-1')
            or request.url.path.endswith('/api/h2h/order/8bc8a8d0-77e2-4ff5-9ff6-b9b74fd51a11/light-20260331-1')
        ):
            return httpx.Response(
                200,
                json={'success': True, 'data': {'order_id': 'order-1', 'status': 'pending', 'sub_status': 'ready'}},
            )
        if request.url.path == self.expected_path:
            return httpx.Response(
                200,
                json={'success': True, 'data': {'order_id': 'order-1', 'status': 'pending', 'sub_status': self.action_type}},
            )
        return httpx.Response(404, json={'success': False, 'message': 'not found'})


def _prepare_profile(copied_light_profile: Path, action_type: str) -> None:
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['merchant_jobs'][0]['schedule']['start_delay_sec'] = 0
    data['merchant_jobs'][0]['schedule']['interval_sec'] = 1
    data['merchant_jobs'][0]['schedule']['requests_total'] = 1
    data['merchant_jobs'][0]['external_id']['pattern'] = 'light-20260331-1'
    data['defaults']['poll_after_create']['delay_ms'] = 5
    data['defaults']['poll_after_create']['attempts'] = 1
    data['defaults']['poll_after_create']['interval_ms'] = 5
    action = {
        'id': f'{action_type}_action',
        'active': True,
        'type': action_type,
        'after_ms': 10,
        'if_order_status_in': ['pending'],
    }
    if action_type in {'add_receipt', 'dispute'}:
        action['receipt'] = {'kind': 'file', 'path': 'receipts/sbp_ok_001.png'}
    data['request_templates'][0]['post_actions'] = [action]
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _wait_until(predicate, timeout: float = 3.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError('condition was not met before timeout')


@pytest.mark.parametrize('action_type', ['cancel', 'confirm_client', 'add_receipt', 'dispute', 'finish'])
def test_post_actions_are_sent_to_expected_h2h_endpoints(copied_light_profile: Path, action_type: str) -> None:
    _prepare_profile(copied_light_profile, action_type)
    platform = ActionPlatform(action_type)
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ]
            and client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ][0]['actions'][f'{action_type}_action']['status']
            in {'done', 'failed', 'skipped'}
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        action_state = state['merchant_runtime']['orders_recent'][0]['actions'][f'{action_type}_action']
        assert action_state['status'] == 'done'

    action_requests = [item for item in platform.requests if item['path'] == platform.expected_path]
    assert len(action_requests) == 1
    sent = action_requests[0]
    if action_type in {'add_receipt', 'dispute'}:
        assert 'multipart/form-data' in sent['headers'].get('content-type', '')
        assert 'name="receipt"' in str(sent['body'])


def test_post_action_is_skipped_when_status_condition_does_not_match(copied_light_profile: Path) -> None:
    _prepare_profile(copied_light_profile, 'cancel')
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['request_templates'][0]['post_actions'][0]['if_order_status_in'] = ['success']
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    platform = ActionPlatform('cancel')
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ]
            and client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ][0]['actions']['cancel_action']['status']
            == 'skipped'
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        action_state = state['merchant_runtime']['orders_recent'][0]['actions']['cancel_action']
        assert action_state['status'] == 'skipped'

    action_requests = [item for item in platform.requests if item['path'] == platform.expected_path]
    assert action_requests == []


def test_receipt_build_failure_marks_action_failed(copied_light_profile: Path) -> None:
    _prepare_profile(copied_light_profile, 'add_receipt')
    merchant_path = copied_light_profile.parent / 'merchant.json'
    data = json.loads(merchant_path.read_text(encoding='utf-8'))
    data['request_templates'][0]['post_actions'][0]['receipt'] = {
        'kind': 'url',
        'url': 'http://127.0.0.1:9/missing-receipt.png',
    }
    merchant_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    platform = ActionPlatform('add_receipt')
    app = create_app(copied_light_profile, merchant_transport_factory=platform.transport_factory)

    with TestClient(app) as client:
        _wait_until(
            lambda: client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ]
            and client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()['merchant_runtime'][
                'orders_recent'
            ][0]['actions']['add_receipt_action']['status']
            == 'failed'
        )
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'}).json()
        action_state = state['merchant_runtime']['orders_recent'][0]['actions']['add_receipt_action']
        assert action_state['status'] == 'failed'
        assert 'connection' in action_state['error'].lower() or 'attempts failed' in action_state['error'].lower()

    action_requests = [item for item in platform.requests if item['path'] == platform.expected_path]
    assert action_requests == []
