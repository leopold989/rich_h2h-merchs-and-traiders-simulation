# trader.json

`trader.json` описывает provider-side часть симулятора: response profiles, трейдеров, правила маршрутизации и пулы реквизитов.

## Верхний уровень

| Поле | Тип | Описание |
|---|---|---|
| `schema_version` | integer | Версия схемы. |
| `defaults` | object | Дефолты provider-side. |
| `response_profiles` | array | Профили поведения ответов. |
| `traders` | array | Список симулируемых трейдеров. |

## `defaults`

| Поле | Тип | Описание |
|---|---|---|
| `driver` | enum | На Patch 01 поддерживается `standard_h2h`. |
| `api_prefix` | string | Будущий базовый H2H prefix трейдера. |
| `validate_access_token` | boolean | Нужно ли по умолчанию проверять Access-Token. |
| `validate_merchant_id` | boolean | Нужно ли по умолчанию проверять merchant_id. |
| `selection_strategy` | enum | `first_match`, `round_robin`, `random`. |
| `idempotency` | object | Правила будущей идемпотентности. |
| `callback_client` | object | Дефолты HTTP-клиента для provider callbacks. |

## `response_profiles[]`

Каждый профиль задаёт поведение для create/cancel/confirm/add_receipt/dispute.

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id профиля. |
| `active` | boolean | Можно ли использовать профиль. |
| `create_order` | object | Поведение create order. |
| `cancel_order` | object | Поведение cancel. |
| `confirm_client` | object | Поведение confirm-client. |
| `add_receipt` | object | Поведение add-receipt. |
| `open_dispute` | object | Поведение dispute. |

### Operation behavior

| Поле | Тип | Описание |
|---|---|---|
| `mode` | enum | `success`, `business_reject`, `timeout`, `http_error`. |
| `delay_ms` | integer | Искусственная задержка ответа. |
| `status_code` | integer | HTTP-код. Для `timeout` не указывается. |
| `body` | object | Произвольный JSON body. |
| `callback` | object | Отложенный callback после ответа. |

### `callback`

| Поле | Тип | Описание |
|---|---|---|
| `enabled` | boolean | Включить callback. |
| `after_ms` | integer | Через сколько отправить callback. |
| `payload` | object | JSON callback payload. |

## `traders[]`

| Поле | Тип | Описание |
|---|---|---|
| `alias` | string | Уникальный алиас трейдера. |
| `active` | boolean | Активность. |
| `base_path` | string | Базовый path-prefix вида `/traders/<alias>`. |
| `driver` | enum | Пока только `standard_h2h`. |
| `auth` | object | Данные, которые платформа будет использовать при обращении к этому provider. |
| `selection_strategy` | enum | Стратегия выбора реквизита. |
| `default_response_profile_id` | string | Профиль ответа по умолчанию. |
| `routing_rules` | array | Маршрутизация по параметрам запроса. |
| `requisites` | array | Набор реквизитов трейдера. |

### `auth`

| Поле | Тип | Описание |
|---|---|---|
| `access_token` | string | Provider-side Access-Token. |
| `merchant_id` | UUID | merchant_id, который платформа будет слать provider-у. |
| `validate_access_token` | boolean | Включить проверку токена. |
| `validate_merchant_id` | boolean | Включить проверку merchant_id. |

### `routing_rules[]`

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id правила внутри трейдера. |
| `active` | boolean | Активность правила. |
| `match` | object | Условия попадания. |
| `requisite_pool` | string[] | Список `requisites[].id`, из которых можно выбирать. |
| `response_profile_id` | string | Какой response profile применить. |

### `match`

Поддерживаемые поля:

| Поле | Тип | Описание |
|---|---|---|
| `payment_gateway` | string | Фильтр по gateway. |
| `payment_detail_type` | string | Фильтр по типу реквизита. |
| `amount` | object | Диапазон `gte/lte/gt/lt`. |
| `is_transgran` | boolean | Merchant-side флаг. |
| `transgran` | boolean | Provider-side совместимость с `standard_h2h`. |

### `requisites[]`

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id реквизита внутри трейдера. |
| `active` | boolean | Активность реквизита. |
| `payment_gateway` | string | Gateway реквизита. |
| `detail_type` | string | Тип реквизита. |
| `detail` | string | Сам реквизит. |
| `initials` | string | Инициалы получателя. |
| `bank_name` | string | Банк/канал. |
| `amount_range` | object | Допустимый диапазон сумм. |
| `is_transgran` | boolean | Признак трансграна. |
| `priority` | integer | Приоритет выбора. |
| `daily_limit` | integer/null | Лимит на будущее. |

## Cross-validation правила

Patch 01 ловит:
- дубли `response_profiles.id`;
- дубли `traders.alias`;
- дубли `traders.base_path`;
- дубли `routing_rules.id` внутри трейдера;
- дубли `requisites.id` внутри трейдера;
- неизвестный `default_response_profile_id`;
- неизвестный `routing_rules[].response_profile_id`;
- ссылки на отсутствующие requisites в `requisite_pool`.
