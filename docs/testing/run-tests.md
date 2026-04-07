# Как прогонять тесты и проверки на Patch 01

## 1. Прогон схем и валидации

```bash
make validate-light
make validate-medium
make validate-heavy
```

Или напрямую:

```bash
python scripts/validate_config.py --system-config examples/light/system.json --dump-state
python scripts/validate_config.py --system-config examples/medium/system.json
python scripts/validate_config.py --system-config examples/heavy/system.json
```

## 2. Генерация JSON Schema

```bash
make schemas
```

На выходе обновятся файлы:

- `schemas/system.schema.json`
- `schemas/merchant.schema.json`
- `schemas/trader.schema.json`

## 3. Прогон тестов

```bash
make test
```

Сейчас тестами покрыты:

- валидные light/medium профили;
- негативные кейсы конфигов;
- control API;
- hot reload;
- инициализация логов.

## 4. Smoke-старт сервиса

```bash
make run-light
```

Потом проверь:

```bash
curl http://127.0.0.1:8099/health
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
```


## Trader tests

```bash
pytest tests/test_trader_runner_core.py
```

```bash
pytest tests/test_trader_runner_core.py tests/test_trader_advanced_behaviors.py
```
