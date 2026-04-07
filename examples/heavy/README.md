# Heavy profile

Профиль для серьёзных прогонов и stress-like сценариев.

## Важно

Этот профиль не рекомендуется включать бездумно на shared dev. Сначала уменьши расписания, `requests_total` и `max_inflight`, если запускаешь не на выделенном стенде.

## Базовый старт

```bash
python scripts/install_profile.py --profile heavy --workspace .sim-workspaces/heavy --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/heavy/config/system.json
```

Перед запуском внимательно проверь:
- `merchant_jobs[].schedule`
- `platform.base_url`
- `traders[].response profiles`
- доступность `public_base_url`

Подробнее про выбор профиля:
- [docs/testing/profile-catalog.md](../../docs/testing/profile-catalog.md)
