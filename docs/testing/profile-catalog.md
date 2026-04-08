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
- `instant_success`, `delayed_success_callback`, `no_requisites`, `hard_timeout`, `http_error`;
- success/cancel/dispute/receipt сценарии.

Когда использовать:
- надо воспроизвести типовую dev-ситуацию;
- надо проверить доработку подбора реквизитов;
- нужен «боевой» профиль без жёсткой нагрузки.

Стартовый мануал:
- [docs/quickstart/medium-e2e.md](../quickstart/medium-e2e.md)

## Heavy compatibility alias

Каталог: `examples/heavy/`

Это обратносуместимый alias консервативного heavy-профиля. Для новых запусков лучше использовать явный вариант `heavy/shared-dev`.

## Heavy / shared-dev

Каталог: `examples/heavy/shared-dev/`

Назначение:
- серьёзная регрессия на общем dev-стенде;
- stress-like прогоны без явной перегрузки shared dev;
- проверка устойчивости логики и логирования на заметном потоке событий.

Что внутри:
- несколько merchants;
- burst-like jobs, но в рамках safety limits;
- несколько traders и response profiles;
- `safety.enabled=true`, `mode=shared_dev`.

Когда использовать:
- нужен профиль тяжелее `medium`, но стенд общий;
- нужно воспроизвести редкие цепочки callback/error без экстремальной интенсивности.

## Heavy / dedicated

Каталог: `examples/heavy/dedicated/`

Назначение:
- нагрузочные прогоны на выделенном стенде;
- агрессивные merchant jobs;
- проверка логики и логов на высоком числе событий.

Что внутри:
- больше merchants и jobs;
- выше `max_inflight`;
- дополнительный round-robin trader;
- `safety.enabled=true`, `mode=dedicated` с повышенными лимитами.

Когда использовать:
- только на изолированном стенде;
- когда нужно проверить поведение под существенной нагрузкой и bursts.

## Практическая рекомендация

- **Light** — первый запуск и smoke.
- **Medium** — ежедневная работа команды.
- **Heavy / shared-dev** — серьёзная прогонка на общем стенде.
- **Heavy / dedicated** — агрессивные тесты только на выделенном окружении.

Подробный пошаговый разбор heavy-профилей:
- [docs/testing/heavy-profiles.md](heavy-profiles.md)
