# Merchant quickstart — light профиль

1. Установить зависимости и активировать editable install:

   ```bash
   pip install -e .[dev]
   ```

2. Скопировать `examples/light/*` в рабочий каталог `config/`.

3. В `config/system.json` проверить:
   - `service.public_base_url`
   - `platform.base_url`
   - пути до `merchant.json`, `trader.json`, `fixtures`, `logs`

4. В `config/merchant.json` убедиться, что:
   - `merchants[0].merchant_id` существует в dev-платформе;
   - `merchants[0].access_token` соответствует этому мерчанту;
   - `merchant_jobs[0].active = true`.

5. Поднять сервис:

   ```bash
   uvicorn rich_h2h_simulator.app_factory:create_app --factory --host 0.0.0.0 --port 8099
   ```

6. Проверить здоровье:

   ```bash
   curl http://127.0.0.1:8099/health
   ```

7. Проверить runtime-state:

   ```bash
   curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
   ```

8. Убедиться, что в `merchant_runtime.orders_recent` появился созданный H2H order.

9. Проверить логи:
   - `logs/merchant_outbound.log`
   - `logs/merchant_callbacks.log`

10. Для ручной проверки callback отправить POST на путь из `merchants[].callback.path` с заголовком `Access-Token` мерчанта.


11. Для проверки follow-up сценариев включить `request_templates[].post_actions` и затем снова посмотреть `/_sim/state`, секцию `merchant_runtime.orders_recent[].actions`.
