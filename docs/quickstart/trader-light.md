# Trader quickstart — light профиль

Для полного пошагового запуска смотри [light-e2e.md](light-e2e.md).

Этот документ оставлен как короткая памятка по provider-side.

## Самая короткая проверка

1. Подними сервис:

```bash
python scripts/run_profile.py --profile light
```

2. Прогони встроенный smoke:

```bash
python scripts/http_smoke.py --system-config examples/light/system.json --base-url http://127.0.0.1:8099
```

3. При необходимости отправь ручной `create order`:

```bash
curl -X POST 'http://127.0.0.1:8099/traders/trader_light/api/h2h/order' \
  -H 'Content-Type: application/json' \
  -H 'Access-Token: trader-light-token' \
  -d '{
    "external_id": "manual-light-001",
    "amount": 5000,
    "merchant_id": "c0a0c1fd-37ad-4c9e-8a48-7b4c90c1f111",
    "payment_gateway": "sbp_rub",
    "payment_detail_type": "phone",
    "transgran": false
  }'
```
