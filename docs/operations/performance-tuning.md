# Performance tuning

Patch 07 добавляет два важных слоя hardening:

- safety-оценку профиля до старта/reload;
- явное разделение heavy shared-dev и heavy dedicated.

## Главные ручки производительности

### Merchant side

| Поле | Влияние |
|---|---|
| `merchant_jobs[].schedule.interval_sec` | Чем меньше интервал, тем выше частота create-order запросов. |
| `merchant_jobs[].schedule.requests_total` | Общий объём прогона. |
| `merchant_jobs[].schedule.max_inflight` | Верхняя граница параллельных merchant create/action потоков на один job. |
| `merchant_jobs[].schedule.jitter_sec` | Размазывает нагрузку во времени и уменьшает синхронные пики. |

### Trader side

| Поле | Влияние |
|---|---|
| `response_profiles[].*.delay_ms` | Увеличивает число одновременных зависших операций. |
| `selection_strategy` | Не влияет на общий RPS напрямую, но влияет на распределение по реквизитам. |
| `callback.after_ms` | Сдвигает нагрузку callback-ов во времени. |

### Logging

| Поле | Влияние |
|---|---|
| `logging.rotation.max_bytes` | Защищает от бесконтрольного роста файлов. |
| `logging.rotation.backup_count` | Ограничивает суммарный объём архивов. |
| `logging.payload_limits.max_body_chars` | Уменьшает размер одной log entry. |

## Safety block

`system.json -> safety` — это не runtime rate limiter, а guard rail на этапе валидации:

- `max_active_jobs`
- `max_total_inflight`
- `max_requests_per_minute_estimate`

Если лимит превышен, сервис не примет конфиг и оставит прошлую рабочую конфигурацию.

## Практические советы

### Для shared dev

- держи `requests_per_minute_estimate` умеренным;
- не поднимай `max_inflight` без необходимости;
- предпочитай jitter > 0 для burst-like jobs;
- сначала прогоняй `medium`, только потом `heavy/shared-dev`.

### Для dedicated стенда

- можно повышать `max_inflight`, но следи за логами и файловой системой;
- включай size-based rotation для heavy прогона;
- держи отдельный workspace и отдельные control tokens;
- фиксируй порт и workspace явно, чтобы не перепутать стенды.

## Наблюдение за системой

Смотри в `/_sim/state`:

- `merchant_runtime.jobs`
- `merchant_runtime.orders_total`
- `trader_runtime.orders_count`
- `trader_runtime.background_tasks`
- `safety`

Если нужно быстро понять, что происходит:

```bash
python scripts/tail_logs.py --system-config <system.json> --channels system merchant_outbound trader_outbound --lines 50
```

## Что делать, если стало слишком тяжело

1. Поставь `active=false` на самые агрессивные merchant jobs.
2. Увеличь `interval_sec`.
3. Уменьши `max_inflight`.
4. Уменьши `requests_total`.
5. Выполни reload.
6. Проверь `/_sim/state` и tail logs.
