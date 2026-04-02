# Patch 01

## Цель

Зафиксировать контракт конфигов и поднять минимальный, но рабочий системный каркас сервиса.

## Что входит

- структура отдельного Python/FastAPI приложения;
- окончательные модели `system.json`, `merchant.json`, `trader.json`;
- кросс-проверки ссылок между секциями;
- JSON Schema экспорт;
- control API: `/health`, `/_sim/config`, `/_sim/state`, `/_sim/reload`;
- hot reload конфигов;
- инициализация логов по каналам;
- light / medium / heavy примеры;
- базовые smoke/unit tests;
- базовая эксплуатационная документация.

## Что не входит

- merchant runner;
- trader emulator endpoints;
- H2H create/get/cancel/dispute runtime;
- provider callbacks;
- end-to-end взаимодействие с `platform_rich-dev`.

## Definition of done

Patch считается закрытым, когда:

1. сервис стартует на валидных конфигах;
2. невалидные конфиги валятся с понятной ошибкой;
3. control API отвечает корректно;
4. hot reload не ломает текущее состояние при плохом конфиге;
5. схемы и markdown-документация лежат в репозитории;
6. light / medium / heavy профили проходят валидацию;
7. smoke tests проходят.
