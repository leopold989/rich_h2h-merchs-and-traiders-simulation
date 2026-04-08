# system.json

`system.json` — главный файл сервиса. Он определяет, как стартует приложение, где лежат остальные конфиги, какие safety-ограничения действуют и как работает control API.

## Верхний уровень

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `schema_version` | integer | да | Версия схемы файла. Для текущего контракта = `1`. |
| `service` | object | да | Сетевые и сервисные параметры. |
| `platform` | object | да | Дефолтные параметры целевой dev-платформы. |
| `paths` | object | да | Пути до `merchant.json`, `trader.json`, fixtures и логов. |
| `runtime` | object | да | Настройки хранения состояния. Сейчас реально используется memory backend. |
| `safety` | object | нет | Ограничения нагрузки и guard rails, прежде всего для shared dev. |
| `logging` | object | да | Каналы логов, ротация и маскирование payload. |
| `control_api` | object | да | Включение control endpoint-ов и токены доступа. |

## `service`

| Поле | Тип | Описание |
|---|---|---|
| `name` | string | Имя сервиса (логическое). |
| `listen_host` | string | Host для uvicorn. Обычно `0.0.0.0` для dev-контейнера. |
| `listen_port` | integer | Порт приложения. |
| `public_base_url` | string (url) | Базовый URL, который merchant runner использует для callback URL. |
| `timezone` | string | Таймзона для сервиса/логов (IANA TZ). |
| `config_reload_interval_sec` | number | Интервал автоперечитывания конфигов. |

## `platform`

| Поле | Тип | Описание |
|---|---|---|
| `base_url` | string (url) | Базовый URL dev-платформы. |
| `verify_ssl` | boolean | Проверять ли TLS сертификат. |
| `timeout_ms` | integer | Таймаут запросов к platform по умолчанию. |
| `api_prefix` | string | Префикс API платформы, например `/api/h2h`. |

## `paths`

| Поле | Тип | Описание |
|---|---|---|
| `merchant_config` | string | Путь до `merchant.json` (relative to `system.json`). |
| `trader_config` | string | Путь до `trader.json` (relative to `system.json`). |
| `fixtures_dir` | string | Папка с fixtures (чеками и т.д.). |
| `log_dir` | string | Папка для логов. |

## `runtime`

| Поле | Тип | Описание |
|---|---|---|
| `state_backend` | enum(`memory`,`redis`) | Backend для runtime state. Сейчас используется `memory`. |
| `idempotency_ttl_sec` | integer | TTL для idempotency ключей. |
| `order_state_ttl_sec` | integer | TTL для order states. |
| `redis` | object | Конфиг Redis на будущее. Если `state_backend=redis`, `redis.enabled` обязан быть `true`. |

## `safety`

`Patch 07` добавляет отдельный блок safety-ограничений. Он нужен не для точного rate limiting во время исполнения, а для **предварительной оценки профиля на этапе старта/reload**.

### Когда использовать

- `enabled=false` — light/medium и кастомные профили без жёстких guard rails;
- `enabled=true`, `mode=shared_dev` — профили, которые должны быть безопасны для общего dev-стенда;
- `enabled=true`, `mode=dedicated` — тяжёлые профили для выделенного стенда с более высокими лимитами.

### Поля

| Поле | Тип | Default | Описание |
|---|---|---|---|
| `enabled` | boolean | `false` | Включить safety-проверки при загрузке конфигов. |
| `mode` | enum(`shared_dev`,`dedicated`) | `shared_dev` | Контекст эксплуатации профиля. Используется для документации и state snapshot. |
| `max_active_jobs` | integer | `10` | Максимально допустимое число активных merchant jobs. |
| `max_total_inflight` | integer | `20` | Максимально допустимая сумма `merchant_jobs[].schedule.max_inflight`. |
| `max_requests_per_minute_estimate` | integer | `300` | Допустимая оценка частоты create-order запросов в минуту. |

### Как считается `requests_per_minute_estimate`

Сейчас это **статическая оценка**:

```text
sum(60 / interval_sec) по всем активным merchant jobs
```

То есть блок safety даёт быстрый ответ на вопрос: “профиль выглядит безопасным для shared dev или нет?”. Это не runtime-throttling и не замена внешним rate limits.

### Что видно в `/_sim/state`

В state snapshot добавляется раздел `safety`:

- `enabled`
- `mode`
- `active_jobs`
- `total_inflight`
- `requests_per_minute_estimate`
- `limits`

Это позволяет быстро сверять профиль с ожидаемыми лимитами после reload.

## `logging`

### `logging.level`

Допустимые значения: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### `logging.format`

Поддерживается `jsonl`.

### `logging.rotation`

| Поле | Тип | Описание |
|---|---|---|
| `when` | string | Параметр timed rotation (`midnight`, `D`, и т.п.). |
| `backup_count` | integer | Сколько архивов хранить. |
| `max_bytes` | integer | Если >0, включается также size-based rotation. |

### `logging.channels`

| Поле | Тип | Описание |
|---|---|---|
| `system` | string | Системные события. |
| `merchant_outbound` | string | Исходящие запросы merchant runner-а к platform. |
| `merchant_callbacks` | string | Callback receiver и статус callback-ов. |
| `trader_inbound` | string | Входящие запросы в trader simulation API. |
| `trader_outbound` | string | Ответы trader simulation API. |

### `logging.payload_limits`

| Поле | Тип | Описание |
|---|---|---|
| `max_body_chars` | integer | Верхний лимит на размер payload, который пишется в лог. |
| `mask_headers` | string[] | Список заголовков, которые нужно маскировать. |

## `control_api`

| Поле | Тип | Описание |
|---|---|---|
| `enabled` | boolean | Включить или выключить control API. |
| `prefix` | string | Базовый path prefix control API. В примерах используется `/_sim`. |
| `read_only_token` | string | Токен для чтения `/_sim/config` и `/_sim/state`. |
| `write_token` | string | Токен для `/_sim/reload`. Должен отличаться от `read_only_token`. |

## Что валидатор проверяет дополнительно

- отсутствует файл `merchant.json` или `trader.json`;
- `state_backend=redis`, но `redis.enabled=false`;
- одинаковые read/write токены;
- несуществующий `fixtures_dir`;
- превышены safety limits при `safety.enabled=true`.
