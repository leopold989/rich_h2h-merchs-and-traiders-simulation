# merchant.json

`merchant.json` описывает весь merchant-side слой: что слать, от имени кого слать и по какому расписанию.

## Верхний уровень

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `schema_version` | integer | да | Версия схемы. |
| `defaults` | object | да | Общие дефолты merchant-side. |
| `request_templates` | array | да | Шаблоны запросов в `platform_rich-dev`. |
| `merchants` | array | да | Описания мерчантов. |
| `merchant_jobs` | array | да | Расписание и параметры генерации трафика. |

## `defaults`

| Поле | Тип | Описание |
|---|---|---|
| `request_timeout_ms` | integer | Дефолтный timeout запроса мерчанта. |
| `poll_after_create` | object | Дефолтная политика polling после create order. |
| `callback_response` | object | Как callback receiver отвечает платформе по умолчанию. |
| `external_id` | object | Базовый шаблон генерации `external_id`. |

### `poll_after_create`

| Поле | Тип | Описание |
|---|---|---|
| `enabled` | boolean | Включён ли polling после создания заказа. |
| `delay_ms` | integer | Задержка перед первым запросом. |
| `attempts` | integer | Число попыток. |
| `interval_ms` | integer | Интервал между попытками. |

### `callback_response`

| Поле | Тип | Описание |
|---|---|---|
| `status_code` | integer | HTTP-код ответа callback receiver. |
| `body` | object | JSON body ответа. |

### `external_id`

На Patch 01 поддерживается режим `pattern`.

| Поле | Тип | Описание |
|---|---|---|
| `mode` | string | Сейчас только `pattern`. |
| `pattern` | string | Шаблон `external_id`. |

## `request_templates[]`

Каждый template описывает одно тело `POST /api/h2h/order` и будущие follow-up действия.

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id шаблона. |
| `active` | boolean | Можно ли использовать шаблон. |
| `description` | string | Человекочитаемое описание. |
| `request` | object | Основной H2H payload. |
| `post_actions` | array | Последующие действия после create order. |

### `request`

| Поле | Тип | Описание |
|---|---|---|
| `amount` | integer | Сумма заказа. > 0. |
| `payment_gateway` | string | Конкретный gateway. Нельзя передавать вместе с `currency`. |
| `currency` | string | Валюта. Нельзя передавать вместе с `payment_gateway`. |
| `payment_detail_type` | string | Тип реквизита: `phone`, `card`, ... |
| `is_transgran` | boolean | Признак трансграна на стороне merchant H2H. |
| `callback_url` | URL | Явный callback URL, если нужно переопределить. |

### Валидация `request`

- должен быть указан ровно один из `payment_gateway` или `currency`;
- `amount` должен быть больше 0.

### `post_actions[]`

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id внутри шаблона. |
| `active` | boolean | Активность действия. |
| `type` | enum | `cancel`, `confirm_client`, `add_receipt`, `dispute`, `finish`. |
| `after_ms` | integer | Задержка перед действием. |
| `if_order_status_in` | string[] | При каких статусах действие допустимо выполнять. |
| `receipt` | object | Нужен для `add_receipt` и `dispute`. |

### `receipt`

| Поле | Тип | Описание |
|---|---|---|
| `kind` | enum | `file`, `url`, `base64`. |
| `path` | string | Для `kind=file`. Путь считается от `fixtures_dir`. |
| `url` | URL | Для `kind=url`. |
| `payload` | string | Для `kind=base64`. |

## `merchants[]`

| Поле | Тип | Описание |
|---|---|---|
| `alias` | string | Уникальный алиас мерчанта. |
| `active` | boolean | Активность мерчанта. |
| `merchant_id` | UUID | ID мерчанта в `platform_rich-dev`. |
| `access_token` | string | Access-Token, с которым пойдёт H2H. |
| `target` | object | Куда слать H2H-запросы. |
| `callback` | object | Настройки merchant callback endpoint-а в симуляторе. |
| `default_headers` | object | Доп. заголовки по умолчанию. |

### `target`

| Поле | Тип | Описание |
|---|---|---|
| `base_url` | URL | Базовый адрес платформы. |
| `api_prefix` | string | Обычно `/api/h2h`. |
| `verify_ssl` | boolean | Проверка TLS. |
| `timeout_ms` | integer | Timeout для запросов. |

### `callback`

| Поле | Тип | Описание |
|---|---|---|
| `enabled` | boolean | Включён ли callback receiver. |
| `path` | string | Relative path вида `/callbacks/merchants/<alias>`. |
| `validate_access_token` | boolean | Нужно ли проверять `Access-Token` платформы. |
| `response_status_code` | integer | HTTP-код ответа callback receiver. |
| `response_body` | object | JSON ответ callback receiver. |

## `merchant_jobs[]`

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный id job-а. |
| `active` | boolean | Активность job-а. |
| `merchant_alias` | string | Ссылка на `merchants[].alias`. |
| `template_id` | string | Ссылка на `request_templates[].id`. |
| `schedule` | object | Частота и объём запуска. |
| `external_id` | object | Переопределение шаблона `external_id` для job-а. |

### `schedule`

| Поле | Тип | Описание |
|---|---|---|
| `start_delay_sec` | integer | Сколько ждать от старта сервиса до первого запуска. |
| `interval_sec` | integer | Интервал между запросами. |
| `requests_total` | integer | Сколько запросов сделать всего. |
| `jitter_sec` | integer | Случайный разброс. |
| `max_inflight` | integer | Максимум одновременно активных запросов. |

## Cross-validation правила

Patch 01 ловит:
- дубли `request_templates.id`;
- дубли `post_actions.id` внутри одного template;
- дубли `merchants.alias`;
- дубли `merchants.callback.path`;
- дубли `merchant_jobs.id`;
- неизвестный `merchant_alias`;
- неизвестный `template_id`;
- отсутствующий fixture файл.
