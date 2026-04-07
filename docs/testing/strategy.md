# Стратегия тестирования

## Цель

Подтвердить, что:
- конфиги валидируются и не ломают сервис тихо;
- merchant/trader runtime работают на согласованных JSON-контрактах;
- examples/light и examples/medium можно реально использовать как стартовые профили;
- helper scripts и docs не расходятся с кодом слишком сильно.

## Слои тестирования

### 1. Schema и cross-config validation
Проверяет:
- pydantic-модели;
- обязательные поля;
- enum и диапазоны;
- правило `payment_gateway XOR currency`;
- корректность ссылок между секциями;
- существование receipt fixtures.

### 2. Control API
Проверяет:
- `/health`;
- токены на `/_sim/config`, `/_sim/state`, `/_sim/reload`;
- маскирование секретов.

### 3. Reload и logging
Проверяет:
- автоматический и ручной reload;
- сохранение последней рабочей конфигурации;
- создание логов и запись событий.

### 4. Merchant runtime
Проверяет:
- scheduler;
- create order;
- poll-after-create;
- callback receiver;
- post actions.

### 5. Trader runtime
Проверяет:
- auth;
- idempotency;
- create/get/cancel;
- confirm/add-receipt/dispute;
- response profiles;
- delayed callbacks.

### 6. E2E smoke по профилям
Проверяет:
- light профиль можно поднять и прогнать без внешней платформы;
- medium профиль остаётся валидным и выполняет базовый provider-side smoke;
- helper smoke plan не ломается при рефакторинге.

### 7. Devtools / helper scripts
Проверяет:
- workspace preparation;
- log path resolution;
- smoke-plan generation для активных trader profiles.

## Negative cases

- несуществующий profile;
- невалидный JSON;
- битые paths;
- дубликаты ids/aliases;
- неверный `requisite_pool`;
- отсутствие fixture файла;
- конфликт `payment_gateway` + `currency`;
- неверные control tokens;
- invalid `Access-Token` на trader side.
