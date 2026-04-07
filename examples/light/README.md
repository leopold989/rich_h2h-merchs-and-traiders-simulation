# Light profile

Минимальный профиль для первого запуска и smoke-проверки.

## Когда использовать

- новый человек только поднимает сервис;
- нужен быстрый sanity-check после изменений;
- надо проверить control API и trader/provider side без подключения к dev-платформе.

## Самый простой путь

```bash
python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
python scripts/run_profile.py --system-config .sim-workspaces/light/config/system.json
python scripts/http_smoke.py --system-config .sim-workspaces/light/config/system.json --base-url http://127.0.0.1:8099
```

Полный мануал:
- [docs/quickstart/light-e2e.md](../../docs/quickstart/light-e2e.md)
