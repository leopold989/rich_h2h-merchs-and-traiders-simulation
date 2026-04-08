# Heavy profiles

Этот документ объясняет, как выбирать и запускать тяжёлые профили после Patch 07.

## Какой heavy-профиль брать

### `heavy/shared-dev`

Брать, если:
- стенд общий;
- нужно больше событий, чем в `medium`;
- важно не положить shared dev случайно.

Особенности:
- conservative heavy;
- включены safety limits;
- подходит для регрессии и поиска редких кейсов.

### `heavy/dedicated`

Брать, если:
- стенд выделенный;
- нужна более агрессивная интенсивность;
- команда осознанно запускает нагрузочный прогон.

Особенности:
- выше `max_inflight`;
- больше merchant jobs;
- отдельный dedicated safety mode;
- лог rotation настроен более агрессивно.

## Пошаговый запуск `heavy/shared-dev`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/install_profile.py --profile heavy/shared-dev --workspace .sim-workspaces/heavy-shared --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/heavy-shared/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/heavy-shared/config/system.json
```

Проверки после старта:

```bash
python scripts/http_smoke.py --system-config .sim-workspaces/heavy-shared/config/system.json --base-url http://127.0.0.1:8099
python scripts/tail_logs.py --system-config .sim-workspaces/heavy-shared/config/system.json --lines 20
```

## Пошаговый запуск `heavy/dedicated`

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python scripts/install_profile.py --profile heavy/dedicated --workspace .sim-workspaces/heavy-dedicated --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/heavy-dedicated/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/heavy-dedicated/config/system.json --port 8109
```

После старта:

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/heavy-dedicated/config/system.json --lines 50
```

## Что проверить перед включением heavy-профиля

- `platform.base_url` указывает на нужный стенд;
- `service.public_base_url` доступен для callbacks;
- `safety` соответствует выбранному стенду;
- log dir находится на разделе с достаточным местом;
- интервалы merchant jobs соответствуют ожидаемой интенсивности.

## Как быстро снизить интенсивность

Самые безопасные ручки:

- увеличить `merchant_jobs[].schedule.interval_sec`;
- уменьшить `merchant_jobs[].schedule.requests_total`;
- уменьшить `merchant_jobs[].schedule.max_inflight`;
- временно выключить часть jobs через `active=false`.

После правок:

```bash
curl -X POST http://127.0.0.1:8099/_sim/reload -H 'X-Control-Token: <write-token>'
```

Или через helper:

```bash
python scripts/http_smoke.py --system-config <path-to-system.json> --base-url http://127.0.0.1:8099
```
