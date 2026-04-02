# Архитектура Patch 01

## Назначение

Сервис остаётся отдельной dev-only кодовой базой и в итоговой архитектуре должен играть две роли:

- **merchant simulator** — шлёт H2H запросы в `platform_rich-dev`;
- **trader/provider simulator** — принимает запросы от `platform_rich-dev` как внешний provider.

На Patch 01 реализуется только системный каркас и слой конфигурации.

## Состав каркаса

### 1. Config manager
Читает `system.json`, затем по путям из него — `merchant.json` и `trader.json`.

### 2. Pydantic contract
Каждый файл валидируется отдельной моделью. Дополнительно выполняются cross-file проверки:
- уникальность id / alias;
- корректность ссылок `template_id`, `merchant_alias`, `response_profile_id`;
- корректность `requisite_pool`;
- проверка receipt fixtures;
- проверка правила `payment_gateway XOR currency`.

### 3. Runtime state
Хранит:
- время старта приложения;
- время последнего успешного reload;
- последнюю ошибку reload;
- digests конфигов;
- счётчики сущностей.

### 4. Control API

- `GET /health` — доступность сервиса;
- `GET /_sim/config` — текущий загруженный конфиг с маскированием токенов;
- `GET /_sim/state` — runtime snapshot;
- `POST /_sim/reload` — принудительная перезагрузка.

### 5. Logging
Готовится отдельный канал на каждый лог-файл:
- `system.log`
- `merchant_outbound.log`
- `merchant_callbacks.log`
- `trader_inbound.log`
- `trader_outbound.log`

Пока на Patch 01 фактически пишется системный лог. Остальные каналы уже инициализируются, чтобы не менять layout на следующих патчах.

## Путь эволюции

- Patch 02–03: merchant runtime
- Patch 04–05: trader runtime
- Patch 06: документация и e2e quickstart
- Patch 07: heavy/load сценарии
