# Каталог профилей

## Light

Каталог: `examples/light/`

Назначение:
- первый запуск;
- smoke после установки;
- быстрый контроль control API;
- проверка trader/provider side без подключения к dev-платформе.

Что внутри:
- 1 merchant;
- 1 request template;
- 1 merchant job;
- 1 trader;
- 1 response profile `instant_success`.

Когда использовать:
- новый человек впервые поднимает сервис;
- нужен быстрый sanity-check после изменений;
- надо проверить, что control API, reload и provider endpoints живы.

Стартовый мануал:
- [docs/quickstart/light-e2e.md](../quickstart/light-e2e.md)

## Medium

Каталог: `examples/medium/`

Назначение:
- обычная dev-регрессия;
- рабочая конфигурация для команды;
- проверка delayed callback, cancel, dispute, add-receipt;
- интеграция с `platform_rich-dev`.

Что внутри:
- несколько request templates;
- несколько merchants;
- несколько traders;
- `instant_success`, `delayed_success_callback`, `no_requisites`, `hard_timeout`, `http_500`;
- success/cancel/dispute/receipt сценарии.

Когда использовать:
- надо воспроизвести типовую dev-ситуацию;
- надо проверить доработку подбора реквизитов;
- нужен "боевой" профиль без жёсткой нагрузки.

Стартовый мануал:
- [docs/quickstart/medium-e2e.md](../quickstart/medium-e2e.md)

## Heavy

Каталог: `examples/heavy/`

Назначение:
- подготовка к серьёзным прогонам;
- stress-like конфигурация;
- шаблон для дальнейших нагрузочных профилей.

Что внутри:
- несколько merchants;
- несколько jobs с высокой частотой;
- несколько traders и response profiles;
- unstable сценарии и burst-like нагрузка.

Когда использовать:
- только на выделенном dev-стенде или после осознанного снижения интенсивности;
- когда нужно проверить устойчивость логики и логирование на большом числе событий.

Важно:
- heavy профиль **не рекомендуется** включать на shared dev без ревью интервалов и `requests_total`.

## Практическая рекомендация

- **Light** — первый запуск и smoke.
- **Medium** — ежедневная работа команды.
- **Heavy** — только осознанные серьёзные прогоны.
