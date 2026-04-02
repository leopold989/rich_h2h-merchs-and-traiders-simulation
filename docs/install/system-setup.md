# Настройка системы

Этот документ описывает **саму систему**, без подробной настройки боевых merchant/trader сценариев.

## 1. Выбери базовый профиль

Для первого запуска используй `examples/light/`.

Скопируй его в рабочий каталог: 

```bash
cp examples/light/system.json config/system.json
cp examples/light/merchant.json config/merchant.json
cp examples/light/trader.json config/trader.json
```

## 2. Проверь `system.json`

Минимум для корректного старта:

- `service.listen_port`
- `service.public_base_url`
- `paths.merchant_config`
- `paths.trader_config`
- `paths.fixtures_dir`
- `paths.log_dir`
- `control_api.read_only_token`
- `control_api.write_token`

## 3. Проверь относительные пути

Все относительные пути считаются от местоположения `system.json`.

Пример:

```json
"paths": {
  "merchant_config": "./merchant.json",
  "trader_config": "./trader.json",
  "fixtures_dir": "../fixtures",
  "log_dir": "../logs"
}
```

## 4. Запусти валидацию до старта сервиса

```bash
python scripts/validate_config.py --system-config config/system.json --dump-state
```

## 5. Подними сервис

```bash
SIM_SYSTEM_CONFIG=config/system.json rich-h2h-simulator
```

## 6. Проверь доступность

```bash
curl http://127.0.0.1:8099/health
```

## 7. Проверь control API

```bash
curl -H 'X-Control-Token: <read-token>' http://127.0.0.1:8099/_sim/state
```

## 8. Проверь, что hot reload работает

1. Измени `config/merchant.json`.
2. Подожди `service.config_reload_interval_sec`.
3. Проверь `/_sim/state`.
4. Либо вызови ручной reload:

```bash
curl -X POST -H 'X-Control-Token: <write-token>' http://127.0.0.1:8099/_sim/reload
```

## 9. Где смотреть логи

Каталог задаётся в `system.json -> paths.log_dir`.

Минимум на Patch 01 проверяй:
- `system.log`

## 10. Что ожидать на Patch 01

После настройки ты должен получить:
- успешный старт сервиса;
- валидные схемы;
- работающий control API;
- системный лог;
- light/medium/heavy примеры, готовые к дальнейшим патчам.
