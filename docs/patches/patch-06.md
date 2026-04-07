# Patch 06 — эксплуатационная документация, helper scripts и profile workspaces

Patch 06 доводит проект до состояния, когда новым человеком можно пользоваться без чтения кода.

## Что вошло

### 1. Helper scripts
- `scripts/install_profile.py` — подготавливает self-contained workspace из `examples/<profile>`;
- `scripts/run_profile.py` — запускает сервис из `examples/<profile>`, workspace или произвольного `system.json`;
- `scripts/http_smoke.py` — проверяет running instance через `/health`, control API и trader happy path;
- `scripts/tail_logs.py` — показывает хвост JSONL-логов и умеет follow mode.

### 2. Step-by-step документация
- `docs/install/system-install.md`
- `docs/install/system-setup.md`
- `docs/quickstart/light-e2e.md`
- `docs/quickstart/medium-e2e.md`
- `docs/operations/troubleshooting.md`

### 3. Улучшение local/dev ergonomics
- `.env.example` для `docker-compose`;
- healthcheck в `docker-compose.yml`;
- make targets для install/run/smoke/logs;
- обновлённый `README.md`.

### 4. Тесты
- smoke/e2e tests для light и medium профилей;
- tests на helper utilities и workspace preparation;
- обновлённая тестовая стратегия и runbook.

## Что Patch 06 не делает

- не добавляет новый runtime-функционал merchant/trader, кроме вспомогательных ops/devtools;
- не закрывает серьёзные нагрузочные профили и perf tuning — это остаётся на следующем этапе.
