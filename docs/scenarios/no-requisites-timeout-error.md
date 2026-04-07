# No requisites / timeout / http error

Для negative testing используются response profiles.

## No requisites

```json
{
  "mode": "business_reject",
  "status_code": 200,
  "body": {
    "success": false,
    "message": "No requisites available"
  }
}
```

## Timeout

```json
{
  "mode": "timeout",
  "delay_ms": 15000
}
```

Симулятор специально задерживает ответ. Если caller дождётся конца задержки, он получит `504`.

## HTTP error

```json
{
  "mode": "http_error",
  "status_code": 500,
  "body": {
    "success": false,
    "message": "Internal simulator error"
  }
}
```
