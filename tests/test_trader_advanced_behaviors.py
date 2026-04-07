from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _wait_for(predicate, timeout: float = 2.0, interval: float = 0.02) -> None:
    started = time.time()
    while time.time() - started < timeout:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError('timeout waiting for condition')


class CallbackCollector:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.app = FastAPI()

        @self.app.post('/api/requisite-providers/callback/{token}')
        async def callback(token: str, request: Request):
            body = await request.json()
            self.calls.append({'token': token, 'body': body, 'headers': dict(request.headers)})
            return JSONResponse({'success': True, 'message': 'accepted'})

    def transport_factory(self, base_url: str) -> httpx.AsyncBaseTransport | None:
        return httpx.ASGITransport(app=self.app)


def test_trader_delayed_callback_payload_is_compatible(copied_medium_profile: Path) -> None:
    trader_path = copied_medium_profile.parent / 'trader.json'
    trader = _load_json(trader_path)
    profile = next(item for item in trader['response_profiles'] if item['id'] == 'delayed_success_callback')
    profile['create_order']['delay_ms'] = 0
    profile['create_order']['callback']['after_ms'] = 20
    _write_json(trader_path, trader)

    collector = CallbackCollector()
    app = create_app(copied_medium_profile, trader_callback_transport_factory=collector.transport_factory)
    with TestClient(app) as client:
        response = client.post(
            '/traders/trader_sbp_pool/api/h2h/order',
            headers={'Access-Token': 'provider-sbp-token'},
            json={
                'external_id': 'callback-001',
                'amount': 20000,
                'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
                'payment_gateway': 'sbp_rub',
                'payment_detail_type': 'phone',
                'callback_url': 'https://platform-rich-dev.local/api/requisite-providers/callback/provider-token',
                'is_transgran': False,
            },
        )
        assert response.status_code == 200
        _wait_for(lambda: len(collector.calls) == 1)
        callback = collector.calls[0]
        assert callback['token'] == 'provider-token'
        assert callback['body']['success'] is True
        assert callback['body']['data']['external_id'] == 'callback-001'
        assert callback['body']['data']['order_id']
        assert callback['body']['data']['status'] == 'success'
        assert callback['body']['data']['sub_status'] == 'accepted'

        state = client.get('/_sim/state', headers={'X-Control-Token': 'medium-read-token'})
        trader_runtime = state.json()['trader_runtime']
        assert trader_runtime['traders']['trader_sbp_pool']['callbacks_sent_total'] == 1


def test_trader_no_requisites_http_error_and_timeout_profiles(copied_medium_profile: Path) -> None:
    trader_path = copied_medium_profile.parent / 'trader.json'
    trader = _load_json(trader_path)
    timeout_profile = next(item for item in trader['response_profiles'] if item['id'] == 'hard_timeout')
    timeout_profile['create_order']['delay_ms'] = 10
    _write_json(trader_path, trader)

    app = create_app(copied_medium_profile)
    with TestClient(app) as client:
        no_req = client.post(
            '/traders/trader_sbp_pool/api/h2h/order',
            headers={'Access-Token': 'provider-sbp-token'},
            json={
                'external_id': 'no-req-001',
                'amount': 60000,
                'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
                'payment_gateway': 'sbp_rub',
            },
        )
        assert no_req.status_code == 200
        assert no_req.json()['success'] is False
        assert 'No requisites' in no_req.json()['message']

        timeout = client.post(
            '/traders/trader_card_unstable/api/h2h/order',
            headers={'Access-Token': 'provider-card-token'},
            json={
                'external_id': 'timeout-001',
                'amount': 40000,
                'merchant_id': '0c27764e-e61a-4cb4-95c5-57415c97d222',
                'payment_gateway': 'sberbank_rub',
                'payment_detail_type': 'card',
            },
        )
        assert timeout.status_code == 504
        assert timeout.json()['success'] is False

        http_error = client.post(
            '/traders/trader_card_unstable/api/h2h/order',
            headers={'Access-Token': 'provider-card-token'},
            json={
                'external_id': 'http-500-001',
                'amount': 5000,
                'merchant_id': '0c27764e-e61a-4cb4-95c5-57415c97d222',
                'payment_gateway': 'raiffeisen_rub',
                'payment_detail_type': 'card',
            },
        )
        assert http_error.status_code == 500
        assert http_error.json()['success'] is False


def test_trader_confirm_receipt_and_dispute_flow(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        headers = {'Access-Token': 'trader-light-token'}
        create = client.post(
            '/traders/trader_light/api/h2h/order',
            headers=headers,
            json={
                'external_id': 'ops-001',
                'amount': 5000,
                'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
                'payment_gateway': 'sbp_rub',
                'payment_detail_type': 'phone',
                'transgran': False,
            },
        )
        order_id = create.json()['data']['order_id']

        confirmed = client.patch(f'/traders/trader_light/api/h2h/order/{order_id}/confirm-client', headers=headers)
        assert confirmed.status_code == 200
        assert confirmed.json()['data']['sub_status'] == 'confirmed_by_client'

        receipt = client.post(
            f'/traders/trader_light/api/h2h/order/{order_id}/add-receipt',
            headers=headers,
            json={'receipt': 'ZmFrZS1yZWNlaXB0'},
        )
        assert receipt.status_code == 200
        assert receipt.json()['data']['sub_status'] == 'receipt_attached'

        dispute = client.post(
            f'/traders/trader_light/api/h2h/order/{order_id}/dispute',
            headers=headers,
            json={'receipt': 'ZmFrZS1kaXNwdXRl'},
        )
        assert dispute.status_code == 200
        assert dispute.json()['data']['sub_status'] == 'in_dispute'

        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'})
        trader_runtime = state.json()['trader_runtime']
        order_state = trader_runtime['orders'][order_id]
        assert order_state['confirm_attempts'] == 1
        assert order_state['add_receipt_attempts'] == 1
        assert order_state['dispute_attempts'] == 1
        assert order_state['last_receipt_excerpt']['receipt'] == 'ZmFrZS1yZWNlaXB0'
        assert order_state['last_dispute_excerpt']['receipt'] == 'ZmFrZS1kaXNwdXRl'
