# Patch 07 — heavy profiles, safety limits, perf/hardening

## Что добавлено

### 1. Heavy profiles разделены на два режима

Добавлены два отдельных набора конфигов:

- `examples/heavy/shared-dev/`
- `examples/heavy/dedicated/`

Также сохранён обратносуместимый alias:

- `examples/heavy/` → фактически shared-dev профиль.

### 2. Safety block в `system.json`

Новый блок:

```json
"safety": {
  "enabled": true,
  "mode": "shared_dev",
  "max_active_jobs": 6,
  "max_total_inflight": 16,
  "max_requests_per_minute_estimate": 60
}
```

Он валидирует профиль на этапе старта/reload и не даёт случайно подложить в shared dev слишком агрессивный набор jobs.

### 3. Code-review fixes из предыдущих патчей

#### Merchant side
- hot reload теперь корректно пересоздаёт job-loops при изменении расписания/шаблона с тем же `job.id`;
- завершившиеся job tasks очищаются из registry и не блокируют повторный запуск;
- ошибки построения receipt payload теперь переводят action в `failed`, а не оставляют его навечно в `running`.

#### Trader side
- `defaults.validate_merchant_id` теперь реально влияет на create/show flows;
- нечисловой `amount` возвращает 4xx validation error вместо 500;
- ссылки на неактивные `response_profiles` ловятся на этапе config validation;
- добавлен defensive fallback на случай runtime-расхождения профилей.

#### Devtools
- `prepare_profile_workspace(..., overwrite=True)` теперь отказывается удалять произвольный каталог без marker file;
- smoke amount picker теперь пересекает rule bounds и `requisite.amount_range`, чтобы не генерировать ложные `no requisites`.

## Что обновлено

- `README.md`
- `docs/config/system.md`
- `docs/testing/profile-catalog.md`
- `docs/testing/heavy-profiles.md`
- `docs/operations/performance-tuning.md`
- `Makefile`
- helper scripts для профилей теперь понимают nested names вроде `heavy/shared-dev`.

## Тесты Patch 07

Добавлены проверки на:

- hot reload completed merchant jobs;
- receipt build failure → action failed;
- `defaults.validate_merchant_id=false`;
- invalid amount → 422;
- inactive referenced response profile;
- workspace overwrite guard;
- smoke amount overlap;
- валидность `heavy/shared-dev` и `heavy/dedicated`.
