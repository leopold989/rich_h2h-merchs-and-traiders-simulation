# Trader callbacks

Если в `response_profiles.*.callback.enabled=true`, симулятор после выполнения операции отправляет callback по `callback_url`, который пришёл в create-order request.

## Что уходит в callback

Даже если в конфиге payload частичный, симулятор автоматически добавляет базовые поля совместимости:

- `data.order_id`
- `data.provider_order_id`
- `data.external_id`
- `data.merchant_id`
- `data.status`
- `data.sub_status`

Это сделано специально под текущий parser callbacks в платформе.

## Как комбинируется payload

1. строится базовый payload совместимости;
2. затем на него накладывается `response_profiles.*.callback.payload`;
3. пользовательские поля из конфига могут переопределить базовые `status/sub_status` и другие значения.
