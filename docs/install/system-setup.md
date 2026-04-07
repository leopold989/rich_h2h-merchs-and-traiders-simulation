# Настройка системы

Этот документ про **настройку самого сервиса**: где лежат конфиги, как их подмонтировать, как выбрать профиль и как проверить, что система вообще поднялась.

## 1. Базовый способ — сделать отдельный workspace

Для первой рабочей настройки удобнее не редактировать `examples/`, а развернуть профиль в отдельный каталог.

### Light workspace

```bash
python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
```

### Medium workspace

```bash
python scripts/install_profile.py --profile medium --workspace .sim-workspaces/medium --overwrite
```

После этого у тебя появится структура:

```text
.sim-workspaces/light/
  config/
    system.json
    merchant.json
    trader.json
  fixtures/
  logs/
```

## 2. Какие файлы отвечает за что

### `system.json`
Определяет:
- host/port сервиса;
- публичный base URL;
- пути до `merchant.json` и `trader.json`;
- каталог логов;
- control API;
- runtime backend.

### `merchant.json`
Определяет:
- request templates;
- merchants;
- merchant jobs;
- poll-after-create и post-actions.

### `trader.json`
Определяет:
- response profiles;
- trader aliases;
- requisites;
- routing rules;
- selection strategy.

## 3. Что править в первую очередь

### Light профиль
Для первого запуска обычно достаточно не трогать `merchant.json` и `trader.json`, а в `system.json` проверить только:

- `service.listen_port`
- `service.public_base_url`
- `control_api.read_only_token`
- `control_api.write_token`

### Medium профиль
Перед подключением к реальной dev-платформе дополнительно надо проверить:

- `platform.base_url`
- `merchants[].merchant_id`
- `merchants[].access_token`
- `traders[].auth.access_token`
- `traders[].auth.merchant_id`

## 4. Как проверить конфиги до старта

```bash
python scripts/validate_config.py --system-config .sim-workspaces/light/config/system.json --dump-state
```

Если команда упала — не запускай сервис, сначала поправь конфиг.

## 5. Как запустить сервис

```bash
python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
```

Либо прямо из примера:

```bash
python scripts/run_profile.py --profile light
```

## 6. Как проверить, что система поднялась

### Health

```bash
curl http://127.0.0.1:8099/health
```

### State

```bash
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
```

### Config dump

```bash
curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/config
```

### Manual reload

```bash
curl -X POST -H 'X-Control-Token: light-write-token' http://127.0.0.1:8099/_sim/reload
```

## 7. Где смотреть логи

### Разово

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20
```

### В режиме follow

```bash
python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --follow
```

## 8. Следующий шаг

- для первого end-to-end запуска смотри [docs/quickstart/light-e2e.md](../quickstart/light-e2e.md)
- для подключения к dev-платформе смотри [docs/quickstart/medium-e2e.md](../quickstart/medium-e2e.md)
