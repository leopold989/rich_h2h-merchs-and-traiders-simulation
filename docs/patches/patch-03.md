# Patch 03 — merchant advanced flows

Этот патч расширяет merchant-side контур из Patch 02.

## Что добавлено

- `poll_after_create` с `GET /api/h2h/order/{order_id}` и fallback на `GET /api/h2h/order/{merchant_id}/{external_id}`;
- движок `post_actions`;
- поддержка действий:
  - `cancel`
  - `confirm_client`
  - `add_receipt`
  - `dispute`
  - `finish`
- проверка `if_order_status_in` перед исполнением действия;
- загрузка receipt fixture файлов в `add-receipt` и `dispute`;
- сохранение poll history и action history в runtime-state;
- тесты на маршрутизацию post-action endpoint-ов.

## Результат

После Patch 03 merchant-side готов для большинства dev-регрессий:

- create order;
- callback handling;
- polling статуса;
- follow-up действия;
- receipt upload сценарии.

Trader-side по-прежнему не входит в эти патчи и остаётся следующим этапом.
