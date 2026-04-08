# Heavy / dedicated profile

Агрессивный профиль для выделенного стенда.

Что внутри:
- больше merchants и jobs;
- существенно выше `max_inflight`;
- дополнительный round-robin trader;
- safety mode = `dedicated` с более высокими лимитами.

Использовать только на изолированном стенде.

```bash
python scripts/install_profile.py --profile heavy/dedicated --workspace .sim-workspaces/heavy-dedicated --overwrite
python scripts/validate_config.py --system-config .sim-workspaces/heavy-dedicated/config/system.json
python scripts/run_profile.py --system-config .sim-workspaces/heavy-dedicated/config/system.json --port 8109
```
