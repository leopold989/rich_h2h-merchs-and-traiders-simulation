# Каталог профилей

## Light

Каталог: `examples/light/`

Назначение:
- первый запуск;
- проверка health/control API;
- обучение новому человеку;
- smoke после установки.

Состав:
- 1 request template;
- 1 merchant;
- 1 merchant job;
- 1 response profile;
- 1 trader.

## Medium

Каталог: `examples/medium/`

Назначение:
- основная рабочая dev-конфигурация;
- подготовка к регрессионным прогонам;
- набор типичных сценариев.

Состав:
- несколько request templates;
- 2 merchant entries;
- success/cancel/dispute;
- 2 traders;
- delayed callback / no requisites / timeout / http error.

## Heavy

Каталог: `examples/heavy/`

Назначение:
- подготовка к нагрузочным сценариям;
- серьёзная проверка структур конфигов;
- шаблон для будущих burst/concurrency прогонов.

Состав:
- 3 merchant entries;
- несколько jobs с высокой частотой;
- несколько trader profiles;
- нестабильные сценарии ответа.

## Важное ограничение Patch 01

Все профили уже валидны по схемам, но runtime-сценарии merchant/trader будут вводиться следующими патчами.
