# Стратегия тестирования

## Цель

Подтвердить, что:
- конфиги валидируются и не ломают сервис тихо;
- merchant/trader runtime работают на согласованных JSON-контрактах;
- examples/light и examples/medium можно реально использовать как стартовые профили;
- heavy shared-dev и heavy dedicated профили валидируются и различаются по назначению;
- helper scripts и docs не расходятся с кодом слишком сильно.

## Слои тестирования

### 1. Schema и cross-config validation

Проверяет:
- pydantic-модели;
- обязательные поля;
- enum и диапазоны;
- правило `payment_gateway XOR currency`;
- корректность ссылок между секциями;
- существование receipt fixtures;
- запрет ссылок на неактивные `response_profiles`;
- safety limits для shared-dev / dedicated профилей.

### 2. Control API

Проверяет:
- `/health`;
- токены на `/_sim/config`, `/_sim/state`, `/_sim/reload`;
- маскирование секретов.

### 3. Reload и logging

Проверяет:
- автоматический и ручной reload;
- сохранение последней рабочей конфигурации;
- пересоздание merchant job loops при изменении job с тем же `id`;
- создание логов и запись событий.

### 4. Merchant runtime

Проверяет:
- scheduler;
- create order;
- poll-after-create;
- callback receiver;
- post actions;
- корректную фиксацию `failed` при ошибке подготовки receipt.

### 5. Trader runtime

Проверяет:
- auth;
- idempotency;
- create/get/cancel;
- confirm/add-receipt/dispute;
- response profiles;
- delayed callbacks;
- влияние `defaults.validate_merchant_id`;
- 4xx на невалидный `amount`.

### 6. E2E smoke по профилям

Проверяет:
- light профиль можно поднять и прогнать без внешней платформы;
- medium профиль остаётся валидным и выполняет базовый provider-side smoke;
- helper smoke plan не ломается при рефакторинге;
- amount picker smoke не генерирует ложный `no requisites` при валидном overlap.

### 7. Devtools / helper scripts

Проверяет:
- workspace preparation;
- защиту от опасного `--overwrite` без marker file;
- log path resolution;
- profile discovery для nested heavy-профилей;
- smoke-plan generation для активных trader profiles.

## Negative cases

- несуществующий profile;
- невалидный JSON;
- битые paths;
- дубликаты ids/aliases;
- неверный `template_id`;
- неверный `merchant_alias`;
- неверный `response_profile_id`;
- ссылка на неактивный `response_profile_id`;
- неверный `requisite_pool`;
- отсутствие fixture файла;
- конфликт `payment_gateway` + `currency`;
- неверные control tokens;
- invalid `Access-Token` на trader side;
- нечисловой `amount`;
- превышение safety limits при `safety.enabled=true`.
