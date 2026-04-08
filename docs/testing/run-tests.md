# Как прогонять тесты и проверки

## 1. Валидация профилей

```bash
make validate-light
make validate-medium
make validate-heavy
make validate-heavy-shared
make validate-heavy-dedicated
```

Или точечно:

```bash
python scripts/validate_config.py --system-config examples/light/system.json
python scripts/validate_config.py --system-config examples/medium/system.json
python scripts/validate_config.py --system-config examples/heavy/system.json
python scripts/validate_config.py --system-config examples/heavy/shared-dev/system.json
python scripts/validate_config.py --system-config examples/heavy/dedicated/system.json
```

## 2. Подготовка workspace-профилей

```bash
make install-light
make install-medium
make install-heavy-shared
make install-heavy-dedicated
```

## 3. Smoke-запуск вручную

Подними сервис:

```bash
python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
```

Во втором терминале:

```bash
make smoke-light
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20
```

## 4. Генерация JSON Schema

```bash
make schemas
```

Проверяй, что обновились:

- `schemas/system.schema.json`
- `schemas/merchant.schema.json`
- `schemas/trader.schema.json`

## 5. Полный тестовый прогон

```bash
make test
```

## 6. Точечные группы тестов

### Merchant runtime

```bash
pytest tests/test_merchant_runner_core.py tests/test_merchant_post_actions.py
```

### Trader runtime

```bash
pytest tests/test_trader_runner_core.py tests/test_trader_advanced_behaviors.py
```

### Devtools, heavy profiles и profile smoke

```bash
pytest tests/test_devtools_scripts.py tests/test_examples_e2e_smoke.py tests/test_config_validation.py
```

## 7. Что считается минимумом перед merge

Минимальный набор:

```bash
make validate-light
make validate-medium
pytest
```

Если менялись heavy-профили, safety block или helper scripts, дополнительно полезно прогнать:

```bash
make validate-heavy-shared
make validate-heavy-dedicated
pytest tests/test_devtools_scripts.py tests/test_config_validation.py
```
