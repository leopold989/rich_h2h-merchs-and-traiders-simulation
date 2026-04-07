# Quickstart — trader light

Этот сценарий нужен, чтобы быстро проверить provider-side контур.

## 1. Подними сервис

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
SIM_SYSTEM_CONFIG=examples/light/system.json rich-h2h-simulator
```

## 2. Создай test order в trader endpoint

```bash
curl -X POST 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order' \
  -H 'Content-Type: application/json' \
  -H 'Access-Token: trader-light-token' \
  -d '{
    "external_id": "provider-order-001",
    "amount": 5000,
    "merchant_id": "c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111",
    "payment_gateway": "sbp_rub",
    "payment_detail_type": "phone",
    "transgran": false
  }'
```

Ожидаемо сервис вернёт `success=true` и `data.order_id` + `data.payment_detail`.

## 3. Проверь order по id

```bash
curl 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order/<order_id>' \
  -H 'Access-Token: trader-light-token'
```

## 4. Проверь order по merchant_id + external_id

```bash
curl 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order/c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111/provider-order-001' \
  -H 'Access-Token: trader-light-token'
```

## 5. Отмени order

```bash
curl -X PATCH 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order/<order_id>/cancel' \
  -H 'Access-Token: trader-light-token'
```

## 6. Посмотри runtime state

```bash
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
```

Смотри секцию `trader_runtime`.
