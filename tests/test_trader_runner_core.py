from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from rich_h2h_simulator.app_factory import create_app


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def test_trader_light_create_show_and_cancel(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        headers = {'Access-Token': 'trader-light-token'}
        create = client.post(
            '/traders/trader_light/api/h2h/order',
            headers=headers,
            json={
                'external_id': 'provider-order-001',
                'amount': 5000,
                'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
                'payment_gateway': 'sbp_rub',
                'payment_detail_type': 'phone',
                'callback_url': 'https://platform-rich-dev.local/api/requisite-providers/callback/test-token',
                'transgran': False,
            },
        )
        assert create.status_code == 200
        body = create.json()
        assert body['success'] is True
        order_id = body['data']['order_id']
        assert body['data']['payment_detail']['detail'] == '+79990001122'

        by_id = client.get(f'/traders/trader_light/api/h2h/order/{order_id}', headers=headers)
        assert by_id.status_code == 200
        assert by_id.json()['data']['external_id'] == 'provider-order-001'

        by_external = client.get(
            '/traders/trader_light/api/h2h/order/c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111/provider-order-001',
            headers=headers,
        )
        assert by_external.status_code == 200
        assert by_external.json()['data']['order_id'] == order_id

        canceled = client.patch(f'/traders/trader_light/api/h2h/order/{order_id}/cancel', headers=headers)
        assert canceled.status_code == 200
        assert canceled.json()['data']['sub_status'] == 'canceled'

        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'})
        trader_runtime = state.json()['trader_runtime']
        assert trader_runtime['orders_count'] == 1
        assert trader_runtime['traders']['trader_light']['create_total'] == 1
        assert trader_runtime['traders']['trader_light']['canceled_total'] == 1


def test_trader_idempotent_create_returns_same_order(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    payload = {
        'external_id': 'idem-001',
        'amount': 7000,
        'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
        'payment_gateway': 'sbp_rub',
        'payment_detail_type': 'phone',
        'transgran': False,
    }
    headers = {'Access-Token': 'trader-light-token'}
    with TestClient(app) as client:
        first = client.post('/traders/trader_light/api/h2h/order', json=payload, headers=headers)
        second = client.post('/traders/trader_light/api/h2h/order', json=payload, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()['data']['order_id'] == second.json()['data']['order_id']
        state = client.get('/_sim/state', headers={'X-Control-Token': 'light-read-token'})
        assert state.json()['trader_runtime']['orders_count'] == 1


def test_trader_invalid_access_token_rejected(copied_light_profile: Path) -> None:
    app = create_app(copied_light_profile)
    with TestClient(app) as client:
        response = client.post(
            '/traders/trader_light/api/h2h/order',
            headers={'Access-Token': 'wrong-token'},
            json={
                'external_id': 'bad-token-001',
                'amount': 5000,
                'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
                'payment_gateway': 'sbp_rub',
                'payment_detail_type': 'phone',
            },
        )
        assert response.status_code == 403
        assert response.json()['message'] == 'invalid Access-Token'


def test_trader_round_robin_selection(copied_medium_profile: Path) -> None:
    app = create_app(copied_medium_profile)
    with TestClient(app) as client:
        headers = {'Access-Token': 'provider-sbp-token'}
        payload = {
            'amount': 5000,
            'merchant_id': 'c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111',
            'payment_gateway': 'sbp_rub',
            'payment_detail_type': 'phone',
            'transgran': False,
        }
        first = client.post('/traders/trader_sbp_pool/api/h2h/order', json={**payload, 'external_id': 'rr-1'}, headers=headers)
        second = client.post('/traders/trader_sbp_pool/api/h2h/order', json={**payload, 'external_id': 'rr-2'}, headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        first_detail = first.json()['data']['payment_detail']['detail']
        second_detail = second.json()['data']['payment_detail']['detail']
        assert {first_detail, second_detail} == {'+79990001122', '+79990003344'}
        assert first_detail != second_detail
