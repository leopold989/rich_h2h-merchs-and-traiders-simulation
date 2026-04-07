# Rich H2H Simulator

Dev-only сервис для тестирования H2H-интеграций вокруг `platform_rich-dev`.

Сервис умеет работать в двух ролях:

- **merchant simulator** — шлёт H2H-запросы в dev-платформу по расписанию;
- **trader / requisite provider simulator** — поднимает provider-side H2H endpoints и отдаёт тестовые реквизиты по конфигу.

Проект рассчитан на отдельную кодовую базу и отдельный compose-контейнер. Конфигурация хранится в трёх JSON-файлах:

```text
config/
  system.json
  merchant.json
  trader.json
```

## Что уже реализовано к Patch 06

- каркас FastAPI-сервиса и control API;
- финальные схемы `system.json`, `merchant.json`, `trader.json`;
- hot reload конфигов;
- merchant runner:
  - scheduler;
  - create order;
  - poll-after-create;
  - callback receiver;
  - `cancel`, `confirm_client`, `add_receipt`, `dispute`, `finish`;
- trader/provider side:
  - create / get / cancel / confirm-client / add-receipt / dispute;
  - auth по `Access-Token`;
  - idempotency по `merchant_id + external_id`;
  - selection strategy `first_match | round_robin | random`;
  - delayed callbacks;
  - `success | business_reject | timeout | http_error` сценарии;
- JSONL-логи по раздельным каналам;
- light / medium / heavy профили;
- helper scripts для установки профиля, запуска, smoke-check и просмотра логов;
- step-by-step документация для нового человека.

## Быстрый старт

### Вариант 1. Запуск прямо из примера

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/validate_config.py --system-config examples/light/system.json --dump-state
python scripts/run_profile.py --profile light
```

Во втором терминале:

```bash
python scripts/http_smoke.py --system-config examples/light/system.json --base-url http://127.0.0.1:8099
python scripts/tail_logs.py --system-config examples/light/system.json --lines 20
```

### Вариант 2. Подготовить отдельный workspace

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/light/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
```

Во втором терминале:

```bash
python scripts/http_smoke.py --system-config .sim-workspaces/light/config/system.json --base-url http://127.0.0.1:8099
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20
```

## Make targets

```bash
make validate-light
make validate-medium
make validate-heavy
make install-light
make install-medium
make run-light
make run-medium
make test
```

## Документация

### Установка и первый запуск
- [docs/install/system-install.md](docs/install/system-install.md)
- [docs/install/system-setup.md](docs/install/system-setup.md)
- [docs/quickstart/light-e2e.md](docs/quickstart/light-e2e.md)
- [docs/quickstart/medium-e2e.md](docs/quickstart/medium-e2e.md)

### Конфиги и схемы
- [docs/config/system.md](docs/config/system.md)
- [docs/config/merchant.md](docs/config/merchant.md)
- [docs/config/trader.md](docs/config/trader.md)
- [schemas/system.schema.json](schemas/system.schema.json)
- [schemas/merchant.schema.json](schemas/merchant.schema.json)
- [schemas/trader.schema.json](schemas/trader.schema.json)

### Сценарии
- [docs/quickstart/merchant-light.md](docs/quickstart/merchant-light.md)
- [docs/quickstart/trader-light.md](docs/quickstart/trader-light.md)
- [docs/scenarios/merchant-post-actions.md](docs/scenarios/merchant-post-actions.md)
- [docs/scenarios/trader-basic.md](docs/scenarios/trader-basic.md)
- [docs/scenarios/trader-callbacks.md](docs/scenarios/trader-callbacks.md)
- [docs/scenarios/no-requisites-timeout-error.md](docs/scenarios/no-requisites-timeout-error.md)

### Эксплуатация и тестирование
- [docs/operations/logs-and-reload.md](docs/operations/logs-and-reload.md)
- [docs/operations/troubleshooting.md](docs/operations/troubleshooting.md)
- [docs/testing/profile-catalog.md](docs/testing/profile-catalog.md)
- [docs/testing/strategy.md](docs/testing/strategy.md)
- [docs/testing/run-tests.md](docs/testing/run-tests.md)

### История патчей
- [docs/patches/patch-01.md](docs/patches/patch-01.md)
- [docs/patches/patch-02.md](docs/patches/patch-02.md)
- [docs/patches/patch-03.md](docs/patches/patch-03.md)
- [docs/patches/patch-04.md](docs/patches/patch-04.md)
- [docs/patches/patch-05.md](docs/patches/patch-05.md)
- [docs/patches/patch-06.md](docs/patches/patch-06.md)

## Важные ограничения

- сервис **не копирует** подбор реквизитов из `platform_rich-dev`, а тестирует реальную dev-платформу как внешний мир;
- merchant-side сценарии требуют доступной dev-платформы или test stub-а;
- `callback_url` для merchant H2H в текущем проекте должен быть `https`;
- `payment_gateway` и `currency` в merchant create-order взаимоисключающие;
- `finish` оставлен как dev-only сценарий.
