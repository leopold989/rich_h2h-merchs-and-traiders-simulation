# Medium E2E quickstart

Этот сценарий нужен для уже **реальной dev-работы**: несколько мерчантов, несколько трейдеров, delayed callback, dispute/cancel сценарии и подключение к `platform_rich-dev`.

## Что получится в конце

После прохождения мануала у тебя будет:

- отдельный medium workspace;
- запущенный simulator;
- рабочие trader/provider endpoints;
- merchant jobs, которые умеют ходить в dev-платформу;
- понятный список логов для анализа.

## Шаг 1. Подготовь workspace

```bash
python scripts/install_profile.py --profile medium --workspace .sim-workspaces/medium --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/medium/config/system.json
```

## Шаг 2. Настрой system.json

В `.sim-workspaces/medium/config/system.json` проверь минимум:

- `service.listen_port`
- `service.public_base_url`
- `platform.base_url`
- `control_api.read_only_token`
- `control_api.write_token`

### Важно по `public_base_url`

Если ты ждёшь merchant callbacks или provider callbacks от dev-платформы, сервис должен быть доступен по адресу из `public_base_url` и этот URL должен быть достижим для самой платформы.

## Шаг 3. Настрой merchant.json

В `.sim-workspaces/medium/config/merchant.json` проверь:

- `merchants[].merchant_id`
- `merchants[].access_token`
- `merchants[].target.base_url`
- `merchant_jobs[].active`

Для первого рабочего прогона удобнее оставить активным только 1 job, остальные временно выключить.

## Шаг 4. Настрой trader.json

В `.sim-workspaces/medium/config/trader.json` проверь:

- `traders[].base_path`
- `traders[].auth.access_token`
- `traders[].auth.merchant_id`
- `response_profiles`
- `routing_rules`

## Шаг 5. Подними сервис

```bash
python scripts/run_profile.py --system-config .sim-workspaces/medium/config/system.json
```

## Шаг 6. Прогони локальный smoke

```bash
python scripts/http_smoke.py --system-config .sim-workspaces/medium/config/system.json --base-url http://127.0.0.1:8099
```

Этот smoke не заменяет платформенную интеграцию, но сразу покажет, что control API и provider-side endpoints живы.

## Шаг 7. Подключи trader endpoints в platform_rich-dev

Для каждого provider-а на стороне платформы используй `base_url` вида:

```text
https://<твой-public-base-url>/traders/trader_sbp_pool
https://<твой-public-base-url>/traders/trader_card_unstable
```

И credentials, соответствующие `trader.json -> traders[].auth`.

## Шаг 8. Разреши merchant jobs ходить в dev-платформу

Убедись, что в `merchant.json`:

- `target.base_url` указывает на dev-платформу;
- `access_token` действительно принадлежит нужному мерчанту;
- `callback.path` включён, если ждёшь callbacks;
- job расписание не слишком агрессивное для shared dev.

Для первого прогона лучше использовать мягкие интервалы, например:

- `start_delay_sec = 5`
- `interval_sec = 30` или больше
- `requests_total = 3..10`
- `max_inflight = 1`

## Шаг 9. Что смотреть во время прогона

### Исходящие запросы мерчантов

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --channels merchant_outbound --follow
```

### Callback-и мерчантов

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --channels merchant_callbacks --follow
```

### Входящие запросы к трейдерам

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --channels trader_inbound --follow
```

### Ответы трейдеров и provider callbacks

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --channels trader_outbound --follow
```

## Шаг 10. Как быстро проверить состояние через control API

```bash
curl -H 'X-Control-Token: medium-read-token' http://127.0.0.1:8099/_sim/state
```

Смотри прежде всего:

- `merchant_runtime.jobs`
- `merchant_runtime.orders_recent`
- `trader_runtime.traders`
- `trader_runtime.orders`

## Что считать успешным результатом

Минимальный рабочий medium сценарий считается поднятым, если:

- сервис отвечает на `/health`;
- `http_smoke.py` проходит;
- платформа стучится в `/traders/<alias>/api/h2h/*`;
- trader-side логи показывают create/get/cancel или callback activity;
- merchant-side логи показывают create-order и, при наличии, callbacks/post-actions.

## Если что-то не работает

Смотри [docs/operations/troubleshooting.md](../operations/troubleshooting.md).
