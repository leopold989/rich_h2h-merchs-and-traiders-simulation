# Light smoke quickstart

Ниже — пошаговый сценарий для человека, который раньше с системой не работал.

## Шаг 1. Установи зависимости

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Шаг 2. Не меняй ничего в примере

Для первого запуска используй файлы как есть:

```text
examples/light/system.json
examples/light/merchant.json
examples/light/trader.json
```

## Шаг 3. Проверь, что конфиги валидны

```bash
python scripts/validate_config.py --system-config examples/light/system.json --dump-state
```

Ожидаемый результат: команда завершается успешно и печатает state snapshot.

## Шаг 4. Подними сервис

```bash
SIM_SYSTEM_CONFIG=examples/light/system.json rich-h2h-simulator
```

## Шаг 5. Открой health endpoint

```bash
curl http://127.0.0.1:8099/health
```

Ожидаемый результат: `status=ok`.

## Шаг 6. Проверь runtime state

```bash
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
```

Ожидаемый результат:
- пути до трёх конфигов;
- digests;
- счётчики сущностей;
- время последнего reload.

## Шаг 7. Проверь public config dump

```bash
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/config
```

Ожидаемый результат: загруженный конфиг с замаскированными токенами.

## Шаг 8. Проверь ручной reload

```bash
curl -X POST -H 'X-Control-Token: light-write-token' http://127.0.0.1:8099/_sim/reload
```

## Шаг 9. Посмотри system.log

Путь до логов: `examples/light/../../logs`, то есть фактически `logs/`.

```bash
tail -f logs/system.log
```

## Шаг 10. Что делать дальше

После Patch 01 можно:
- менять и валидировать конфиги;
- смотреть как работает reload;
- изучать профили light/medium/heavy.

Полноценный merchant/trader runtime придёт следующими патчами.
