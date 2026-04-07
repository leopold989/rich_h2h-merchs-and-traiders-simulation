# Логи и reload

## Какие логи есть

Сервис пишет JSONL-файлы по каналам:

- `system.log`
- `merchant_outbound.log`
- `merchant_callbacks.log`
- `trader_inbound.log`
- `trader_outbound.log`

Каждая строка — отдельное JSON-событие.

## Где лежат логи

Каталог задаётся в `system.json -> paths.log_dir`.

Если используешь workspace, обычно это:

```text
.sim-workspaces/<profile>/logs/
```

## Как быстро посмотреть хвост

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20
```

## Как смотреть только один канал

```bash
python scripts/tail_logs.py \
  --system-config .sim-workspaces/medium/config/system.json \
  --channels trader_outbound \
  --lines 50
```

## Как смотреть live

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --follow
```

## Структура событий

Базовые поля у каждой строки:

- `ts`
- `level`
- `logger`
- `message`
- `event`
- `payload`

## Что в каком файле искать

### `system.log`
Ищи:
- start/stop приложения;
- reload;
- ошибки конфигов;
- reconfigure merchant/trader runners.

### `merchant_outbound.log`
Ищи:
- create order в платформу;
- poll after create;
- `cancel`, `confirm_client`, `finish`, `add_receipt`, `dispute`.

### `merchant_callbacks.log`
Ищи:
- callback payload от платформы;
- ошибки токенов;
- обновление order state.

### `trader_inbound.log`
Ищи:
- все входящие запросы от платформы к provider endpoints.

### `trader_outbound.log`
Ищи:
- response payload трейдера;
- provider callbacks в dev-платформу;
- ошибки callback delivery.

## Автоматический reload

Период auto-reload задаётся в `service.config_reload_interval_sec`.

Алгоритм:
1. сервис отслеживает изменения `system.json`, `merchant.json`, `trader.json`;
2. если файлы изменились — валидирует заново;
3. если всё валидно — применяет новый bundle;
4. если bundle невалиден — оставляет последнюю рабочую версию и пишет ошибку в `system.log`.

## Ручной reload

```bash
curl -X POST -H 'X-Control-Token: <write-token>' http://127.0.0.1:8099/_sim/reload
```

## Как понять, что reload прошёл

Проверь:

- `/_sim/state -> last_reload_success_at`
- `/_sim/state -> last_reload_error`
- `system.log`

## Практический совет

Если ты правишь medium/heavy конфиг и боишься потерять рабочее состояние, сначала запускай:

```bash
python scripts/validate_config.py --system-config .sim-workspaces/medium/config/system.json
```

а уже потом делай reload.
