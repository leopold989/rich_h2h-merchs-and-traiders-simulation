# Patch 04 — Trader/provider core

Patch 04 добавляет в симулятор базовый provider-side контур для `standard_h2h`:

- поднимает trader endpoints по `traders[].base_path + defaults.api_prefix`;
- проверяет `Access-Token` и `merchant_id`;
- реализует `POST /api/h2h/order`;
- реализует `GET /api/h2h/order/{order_id}`;
- реализует `GET /api/h2h/order/{merchant_id}/{external_id}`;
- реализует `PATCH /api/h2h/order/{order_id}/cancel`;
- хранит runtime-state по order'ам трейдера;
- поддерживает idempotency по `(trader_alias, merchant_id, external_id)`;
- поддерживает selection strategies:
  - `first_match`
  - `round_robin`
  - `random`
- пишет inbound/outbound provider logs.

Что ещё не входит в Patch 04:

- delayed callbacks от трейдера в платформу;
- `confirm-client`;
- `add-receipt`;
- `dispute`;
- advanced behavior для callback-профилей.
