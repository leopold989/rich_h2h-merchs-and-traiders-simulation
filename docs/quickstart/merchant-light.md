# Merchant quickstart — light профиль

Для полного мануала по установке и первому запуску смотри [light-e2e.md](light-e2e.md).

Этот документ — короткая памятка именно по merchant-side.

## Что нужно для merchant-side прогона

- доступная `platform_rich-dev` или stub-платформа;
- корректные `merchant_id` и `access_token`;
- достижимый `service.public_base_url`, если ждёшь callbacks;
- активный `merchant_jobs[]`.

## Минимальные шаги

1. Подготовить workspace:

   ```bash
   python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
   ```

2. Проверить `merchant.json`:
   - `merchants[0].merchant_id`
   - `merchants[0].access_token`
   - `merchants[0].target.base_url`
   - `merchant_jobs[0].active`

3. Запустить сервис:

   ```bash
   python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
   ```

4. Смотреть состояние:

   ```bash
   curl -H 'X-Control-Token: light-read-token' http://127.0.0.1:8099/_sim/state
   ```

5. Смотреть логи:

   ```bash
   python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --channels merchant_outbound merchant_callbacks --follow
   ```

## Что смотреть в state

- `merchant_runtime.jobs`
- `merchant_runtime.orders_recent`
- `merchant_runtime.orders_recent[].actions`
