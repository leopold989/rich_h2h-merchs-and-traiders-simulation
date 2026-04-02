# Стратегия тестирования

## Цель Patch 01

Подтвердить, что системный каркас стабилен и конфиги не могут тихо сломать приложение.

## Слои тестирования

### 1. Schema validation
Проверяет:
- pydantic-модели;
- обязательные поля;
- enum и диапазоны;
- правило `payment_gateway XOR currency`;
- корректность ссылок между секциями.

### 2. Control API smoke tests
Проверяет:
- `/health`;
- токены на `/_sim/config`, `/_sim/state`, `/_sim/reload`;
- маскирование секретов.

### 3. Reload tests
Проверяет:
- детект изменений;
- успешный reload валидных файлов;
- сохранение последней рабочей конфигурации при плохом reload.

### 4. Logging tests
Проверяет:
- создание log-dir;
- инициализацию файлов каналов;
- запись системного события в JSONL.

## Negative cases

Обязательные негативные проверки:
- дубли `request_templates.id`;
- дубли `merchants.alias`;
- дубли `response_profiles.id`;
- неверный `template_id`;
- неверный `merchant_alias`;
- неверный `response_profile_id`;
- неверный `requisite_pool`;
- отсутствие fixture файла;
- конфликт `payment_gateway` + `currency`;
- неверные control tokens.
