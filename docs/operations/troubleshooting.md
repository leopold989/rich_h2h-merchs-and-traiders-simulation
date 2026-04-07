# Troubleshooting

Ниже — короткий список самых частых проблем и что проверить в первую очередь.

## 1. `validate_config.py` падает на старте

Проверь:
- существует ли `system.json`;
- корректны ли пути `merchant_config`, `trader_config`, `fixtures_dir`, `log_dir`;
- есть ли referenced receipt files в `fixtures/`;
- нет ли дубликатов `id` и `alias`.

Обычно помогает:

```bash
python scripts/validate_config.py --system-config <path-to-system.json> --dump-state
```

## 2. `/health` отвечает, но merchant jobs ничего не шлют

Проверь:
- `merchant_jobs[].active = true`;
- `merchants[].active = true`;
- `request_templates[].active = true`;
- расписание `start_delay_sec / interval_sec / requests_total`;
- `platform.base_url` и `merchants[].target.base_url`.

Смотри:
- `/_sim/state -> merchant_runtime.jobs`
- `merchant_outbound.log`
- `system.log`

## 3. Платформа не может достучаться до callback мерчанта

Проверь:
- `service.public_base_url`;
- `merchants[].callback.path`;
- доступность URL извне;
- что `callback_url` реально HTTPS, если платформа валидирует его как `https`.

## 4. Trader endpoint отвечает `403 invalid Access-Token`

Проверь:
- заголовок `Access-Token`;
- `trader.json -> traders[].auth.access_token`;
- не смаскирован ли токен при копировании из public config dump.

## 5. Trader endpoint отвечает `403 invalid merchant_id`

Проверь:
- `merchant_id` в запросе провайдера;
- `trader.json -> traders[].auth.merchant_id`;
- не перепутаны ли provider credentials между трейдерами.

## 6. Trader create-order возвращает `No requisites available`

Проверь:
- `routing_rules`;
- `requisite_pool`;
- диапазоны суммы;
- `payment_gateway` / `payment_detail_type`;
- `is_transgran` / `transgran`.

## 7. Merchant create-order падает 4xx/5xx

Проверь:
- `access_token` и `merchant_id`;
- `payment_gateway` vs `currency`;
- наличие обязательных полей;
- что dev-платформа доступна по `target.base_url`.

Смотри `merchant_outbound.log`.

## 8. Receipt/dispute action не уходит

Проверь:
- `post_actions[].receipt.kind`;
- файл действительно есть под `fixtures_dir`;
- `if_order_status_in` совпадает с текущим статусом order.

## 9. Автоматический reload не подхватывает изменения

Проверь:
- `service.config_reload_interval_sec`;
- нет ли ошибки в новом bundle;
- не редактируется ли другой файл, не тот что реально подключён в `system.json`.

Для надёжности сделай ручной reload:

```bash
curl -X POST -H 'X-Control-Token: <write-token>' http://127.0.0.1:8099/_sim/reload
```

## 10. Логи пустые

Проверь:
- каталог `paths.log_dir`;
- права на запись;
- действительно ли запускается тот `system.json`, который ты смотришь;
- `logging.level` и сами сценарии — возможно просто не было активности.

## 11. Что проверить первым делом почти при любой проблеме

1. `python scripts/validate_config.py --system-config <system.json>`
2. `curl /health`
3. `curl /_sim/state`
4. `python scripts/tail_logs.py --system-config <system.json> --lines 50`

Если после этого картина всё ещё непонятна — уже имеет смысл разбирать конкретный log channel и payload.
