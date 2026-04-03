# Merchant post-actions

## Поддерживаемые действия

Каждый `request_templates[].post_actions[]` исполняется как отдельная фоновая задача после успешного `create order`.

Поддерживаются:

- `cancel`
- `confirm_client`
- `add_receipt`
- `dispute`
- `finish`

## Порядок работы

1. создаётся H2H order;
2. если включён `poll_after_create`, симулятор делает один или несколько `GET order`;
3. для каждого активного `post_action` создаётся отдельная задача;
4. после `after_ms` действие проверяет текущее состояние ордера;
5. если задан `if_order_status_in` и статус не совпал, действие помечается как `skipped`;
6. если нужен receipt, он берётся из `fixtures_dir`;
7. результат действия попадает в runtime-state и логи.

## Receipt actions

Для `add_receipt` и `dispute` поддерживаются:

- `kind=file` — файл из `fixtures_dir` отправляется multipart upload;
- `kind=base64` — base64 строка отправляется как поле `receipt`;
- `kind=url` — симулятор пытается скачать содержимое URL и отправить его как файл.

## Где смотреть результат

- `GET /_sim/state`
  - `merchant_runtime.orders_recent[].poll_history`
  - `merchant_runtime.orders_recent[].actions`
- `logs/merchant_outbound.log`
- `logs/merchant_callbacks.log`
