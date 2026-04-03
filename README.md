# Rich H2H Simulator — Patch 01

Patch 01 закрывает базовый каркас проекта:

- структура отдельного Python/FastAPI сервиса;
- финальные JSON-схемы `system.json`, `merchant.json`, `trader.json`;
- загрузка и валидация конфигов;
- JSON Schema экспорт;
- `GET /health`, `GET /_sim/config`, `GET /_sim/state`, `POST /_sim/reload`;
- hot reload конфигов;
- инициализация раздельных файловых логов;
- light / medium / heavy примеры конфигов;
- базовая документация по установке, настройке, схемам и тестированию;
- unit/smoke tests для каркаса.

В этом патче **ещё не реализованы** merchant runner и trader emulator. То есть сервис уже умеет подниматься, валидировать контракты и работать как контрольный слой, но не создаёт H2H-трафик и не поднимает trader endpoints.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/validate_config.py --system-config examples/light/system.json --dump-state
SIM_SYSTEM_CONFIG=examples/light/system.json rich-h2h-simulator
```

Проверка:

```bash
curl http://127.0.0.1:8099/health
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/config
curl -X POST -H 'X-Control-Token: light-write-token' http://127.0.0.1:8099/_sim/reload
```


Полезные команды:

```bash
make validate-light
make validate-medium
make validate-heavy
make schemas
make test
make run-light
```

## Что смотреть дальше

- [docs/patches/patch-01.md](docs/patches/patch-01.md)
- [docs/install/system-install.md](docs/install/system-install.md)
- [docs/install/system-setup.md](docs/install/system-setup.md)
- [docs/quickstart/light-smoke.md](docs/quickstart/light-smoke.md)
- [docs/config/system.md](docs/config/system.md)
- [docs/config/merchant.md](docs/config/merchant.md)
- [docs/config/trader.md](docs/config/trader.md)
- [docs/testing/profile-catalog.md](docs/testing/profile-catalog.md)
- [docs/testing/run-tests.md](docs/testing/run-tests.md)


## Patch 02 status

Merchant runner core is implemented. See `docs/patches/patch-02.md` and `docs/quickstart/merchant-light.md`.


## Patch 03 status

Merchant advanced flows are implemented: polling, post actions, receipt uploads. See `docs/patches/patch-03.md` and `docs/scenarios/merchant-post-actions.md`.
