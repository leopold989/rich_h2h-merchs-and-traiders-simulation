# Trader basic scenario

В Patch 04 симулятор умеет выступать как `standard_h2h` provider.

## Маршруты

Для трейдера с `base_path=/traders/trader_light` и `api_prefix=/api/h2h` сервис поднимает:

- `POST /traders/trader_light/api/h2h/order`
- `GET /traders/trader_light/api/h2h/order/{order_id}`
- `GET /traders/trader_light/api/h2h/order/{merchant_id}/{external_id}`
- `PATCH /traders/trader_light/api/h2h/order/{order_id}/cancel`

## Auth

Проверяются:

- `Access-Token` header;
- `merchant_id` в create-order payload.

## Idempotency

Повторный `POST /order` с тем же `(merchant_id, external_id)` вернёт тот же `order_id` и тот же payload ответа.

## Requisite selection

Подбор идёт по:

- `routing_rules`;
- `requisite_pool`;
- `amount_range`;
- `payment_gateway`;
- `payment_detail_type`;
- `is_transgran` / `transgran`.

Дальше применяется `selection_strategy` трейдера.
