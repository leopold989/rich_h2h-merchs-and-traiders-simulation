# Heavy / shared-dev profile

Консервативный heavy-профиль для общего dev-стенда.

Что внутри:
- несколько merchant jobs, но с ограниченной суммарной интенсивностью;
- safety limits в `system.json`;
- пригоден для серьёзной регрессии без явного риска перегрузить shared dev.

Рекомендуемый старт:

```bash
python scripts/install_profile.py --profile heavy/shared-dev --workspace .sim-workspaces/heavy-shared --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/heavy-shared/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/heavy-shared/config/system.json
```
