# Light E2E quickstart

Этот мануал рассчитан на человека, который **не знает систему**, но должен за 5–10 минут поднять сервис, проверить control API, trader-side контур и логи.

## Что получится в конце

После прохождения шагов у тебя будет:

- запущенный simulator;
- валидный light workspace;
- рабочий `/health` и `/_sim/*`;
- рабочий trader endpoint;
- понятное место, где смотреть логи.

## Шаг 1. Установи зависимости

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Шаг 2. Подготовь light workspace

```bash
python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
```

## Шаг 3. Проверь конфиг до старта

```bash
python scripts/validate_config.py --system-config .sim-workspaces/light/config/system.json --dump-state
```

Ожидаемо команда завершится без ошибки.

## Шаг 4. Подними сервис

```bash
python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
```

Оставь этот процесс в первом терминале.

## Шаг 5. Проверь health и control API

Во втором терминале:

```bash
curl http://127.0.0.1:8099/health
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/config
curl -X POST -H 'X-Control-Token: light-write-token' http://127.0.0.1:8099/_sim/reload
```

## Шаг 6. Прогони автоматический smoke

```bash
python scripts/http_smoke.py --system-config .sim-workspaces/light/config/system.json --base-url http://127.0.0.1:8099
```

Smoke делает:

- `GET /health`
- `GET /_sim/state`
- `GET /_sim/config`
- `POST /_sim/reload`
- `POST /traders/trader_light/api/h2h/order`
- `GET /traders/trader_light/api/h2h/order/{order_id}`
- `GET /traders/trader_light/api/h2h/order/{merchant_id}/{external_id}`
- `PATCH /traders/trader_light/api/h2h/order/{order_id}/cancel`

## Шаг 7. Посмотри логи

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20
```

Если хочешь смотреть live:

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --follow
```

## Шаг 8. Ручная trader-проверка через curl

```bash
curl -X POST 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order' \
  -H 'Content-Type: application/json' \
  -H 'Access-Token: trader-light-token' \
  -d '{
    "external_id": "manual-light-001",
    "amount": 5000,
    "merchant_id": "c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111",
    "payment_gateway": "sbp_rub",
    "payment_detail_type": "phone",
    "transgran": false
  }'
```

Потом по `order_id` можно вызвать `GET` и `cancel`.

## Что ты проверил этим сценарием

- сервис установлен корректно;
- конфиги читаются и валидируются;
- control API живой;
- trader/provider контур поднимается и отвечает;
- логи пишутся в нужные файлы.

## Что light сценарий ещё не проверяет

- реальную интеграцию с `platform_rich-dev`;
- merchant jobs против dev-платформы;
- delayed callback и негативные provider сценарии;
- многомерчантную рабочую конфигурацию.

Для этого переходи к [docs/quickstart/medium-e2e.md](medium-e2e.md).
