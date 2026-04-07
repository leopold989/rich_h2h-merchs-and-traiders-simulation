# Patch 05 — Trader advanced behaviors + callbacks

Patch 05 расширяет provider-side контур из Patch 04:

- добавляет delayed callbacks из трейдера в платформу;
- добавляет `PATCH /api/h2h/order/{order_id}/confirm-client`;
- добавляет `POST /api/h2h/order/{order_id}/add-receipt`;
- добавляет `POST /api/h2h/order/{order_id}/dispute`;
- поддерживает response profiles для:
  - `success`
  - `business_reject`
  - `timeout`
  - `http_error`
- отправляет callback payload в совместимом с `platform_rich-dev` формате;
- принимает и `is_transgran`, и `transgran`;
- пишет в runtime-state callback attempts, receipt/dispute excerpts и provider stats.

После Patch 05 medium trader profile уже пригоден для обычной dev-регрессии:

- delayed success callback;
- empty/no requisites;
- provider timeout;
- provider http error;
- confirm-client / add-receipt / dispute.
