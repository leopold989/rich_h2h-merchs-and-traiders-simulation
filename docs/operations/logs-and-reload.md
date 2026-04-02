# Логи и reload

## Логи

Patch 01 создаёт каналы: 

- `system.log`
- `merchant_outbound.log`
- `merchant_callbacks.log`
- `trader_inbound.log`
- `trader_outbound.log`

Фактически на этом патче активно используется `system.log`. Остальные каналы создаются как часть стабильного layout проекта.

## Формат

Все лог-файлы пишутся в формате JSONL. Каждая строка — отдельное JSON-событие.

Поля ядра:
- `ts`
- `level`
- `logger`
- `message`
- `event`
- `payload`

## Автоматический reload

Период опроса файлов задаётся в `service.config_reload_interval_sec`.

Алгоритм:
1. сервис хранит mtimes и digests загруженных файлов;
2. по таймеру сравнивает изменения;
3. если конфиги валидны — принимает новую версию;
4. если конфиги невалидны — оставляет последнюю рабочую версию и пишет ошибку.

## Ручной reload

```bash
curl -X POST -H 'X-Control-Token: <write-token>' http://127.0.0.1:8099/_sim/reload
```

## Как понять, что reload прошёл

Проверь:
- `/_sim/state -> last_reload_success_at`;
- `/_sim/state -> last_reload_error`;
- `logs/system.log`.
