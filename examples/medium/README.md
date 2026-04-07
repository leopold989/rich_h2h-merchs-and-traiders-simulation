# Medium profile

Рабочий профиль для обычной dev-регрессии и подключения к `platform_rich-dev`.

## Когда использовать

- нужно гонять реальные merchant jobs в dev-платформу;
- нужно поднять несколько simulated traders;
- нужно проверить delayed callback, cancel, dispute и provider-side ошибки.

## Старт

```bash
python scripts/install_profile.py --profile medium --workspace .sim-workspaces/medium --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/medium/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/medium/config/system.json
```

Потом:

```bash
python scripts/http_smoke.py --system-config .sim-workspaces/medium/config/system.json --base-url http://127.0.0.1:8099
```

Полный мануал:
- [docs/quickstart/medium-e2e.md](../../docs/quickstart/medium-e2e.md)
