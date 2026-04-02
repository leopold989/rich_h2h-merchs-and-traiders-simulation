# system.json

`system.json` — главный файл сервиса. Он определяет, как стартует приложение, где лежат остальные конфиги и как работает control API.

## Верхний уровень

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `schema_version` | integer | да | Версия схемы файла. Для Patch 01 = `1`. |
| `service` | object | да | Сетевые и сервисные параметры. |
| `platform` | object | да | Дефолтные параметры целевой dev-платформы. |
| `paths` | object | да | Пути до `merchant.json`, `trader.json`, fixtures и логов. |
| `runtime` | object | да | Настройки хранения состояния. Сейчас реально используется memory backend. |
| `logging` | object | да | Каналы логов, ротация и маскирование payload. |
| `control_api` | object | да | Включение control endpoint-ов и токены доступа. |

## `service`

| Поле | Тип | Default | Описание |
|---|---|---|---|
| `name` | string | — | Логическое имя сервиса. |
| `listen_host` | string | `0.0.0.0` | IP/host bind для FastAPI/uvicorn. |
| `listen_port` | integer | `8099` | Порт приложения. |
| `public_base_url` | URL | — | Базовый публичный URL сервиса. Для реальных callbacks рекомендуем `https`. |
| `timezone` | string | `Europe/Warsaw` | Часовой пояс сервиса. |
| `config_reload_interval_sec` | integer | `5` | Период проверки файлов для hot reload. |

## `platform`

| Поле | Тип | Default | Описание |
|---|---|---|---|
| `base_url` | URL | — | Дефолтный адрес `platform_rich-dev`. |
| `verify_ssl` | boolean | `false` | Проверка TLS сертификата. |
| `timeout_ms` | integer | `10000` | Дефолтный timeout для внешних вызовов. |
| `api_prefix` | string | `/api/h2h` | Базовый prefix H2H API платформы. |

## `paths`

Все относительные пути считаются **от каталога, где лежит `system.json`**.

| Поле | Тип | Описание |
|---|---|---|
| `merchant_config` | string | Путь до `merchant.json`. |
| `trader_config` | string | Путь до `trader.json`. |
| `fixtures_dir` | string | Базовый каталог для файлов, на которые ссылаются конфиги. |
| `log_dir` | string | Каталог для всех файловых логов. |

## `runtime`

| Поле | Тип | Описание |
|---|---|---|
| `state_backend` | enum(`memory`,`redis`) | Backend для runtime state. На Patch 01 используется `memory`. |
| `idempotency_ttl_sec` | integer | TTL для будущих idempotency ключей. |
| `order_state_ttl_sec` | integer | TTL для будущих order states. |
| `redis` | object | Конфиг Redis на будущее. Если `state_backend=redis`, `redis.enabled` обязан быть `true`. |

## `logging`

### `logging.level`
Допустимые значения: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### `logging.format`
На Patch 01 поддерживается только `jsonl`.

### `logging.rotation`

| Поле | Тип | Описание |
|---|---|---|
| `when` | string | Ротация по времени для `TimedRotatingFileHandler`. |
| `backup_count` | integer | Сколько архивов сохранять. |
| `max_bytes` | integer | Если больше 0, включается size-based rotation. |

### `logging.channels`

| Поле | Тип | Описание |
|---|---|---|
| `system` | string | Файл системного лога. |
| `merchant_outbound` | string | Лог исходящих merchant запросов. |
| `merchant_callbacks` | string | Лог входящих callback-ов мерчанта. |
| `trader_inbound` | string | Лог входящих запросов трейдера. |
| `trader_outbound` | string | Лог ответов/callback-ов трейдера. |

### `logging.payload_limits`

| Поле | Тип | Описание |
|---|---|---|
| `max_body_chars` | integer | Верхний лимит на размер payload, который будем писать в лог. |
| `mask_headers` | string[] | Список заголовков, которые нужно маскировать. |

## `control_api`

| Поле | Тип | Описание |
|---|---|---|
| `enabled` | boolean | Включить или выключить control API. |
| `prefix` | string | Базовый path prefix control API. В light/medium/heavy примерах используется `/_sim`. |
| `read_only_token` | string | Токен для чтения `/_sim/config` и `/_sim/state`. |
| `write_token` | string | Токен для `/_sim/reload`. Должен отличаться от `read_only_token`. |

## Ошибки, которые ловятся при старте

- отсутствует файл `merchant.json` или `trader.json`;
- `state_backend=redis`, но `redis.enabled=false`;
- одинаковые read/write токены;
- неверные пути;
- несуществующий `fixtures_dir`.
