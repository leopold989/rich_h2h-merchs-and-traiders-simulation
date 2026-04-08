.PHONY: \
	validate-light validate-medium validate-heavy validate-heavy-shared validate-heavy-dedicated schemas test \
	run-light run-medium run-heavy run-heavy-shared run-heavy-dedicated \
	install-light install-medium install-heavy install-heavy-shared install-heavy-dedicated \
	smoke-light smoke-medium \
	tail-light-logs tail-medium-logs

validate-light:
	python scripts/validate_config.py --system-config examples/light/system.json --dump-state

validate-medium:
	python scripts/validate_config.py --system-config examples/medium/system.json

validate-heavy:
	python scripts/validate_config.py --system-config examples/heavy/system.json

validate-heavy-shared:
	python scripts/validate_config.py --system-config examples/heavy/shared-dev/system.json

validate-heavy-dedicated:
	python scripts/validate_config.py --system-config examples/heavy/dedicated/system.json

schemas:
	python scripts/export_schemas.py

test:
	pytest

run-light:
	python scripts/run_profile.py --profile light

run-medium:
	python scripts/run_profile.py --profile medium

run-heavy:
	python scripts/run_profile.py --profile heavy

run-heavy-shared:
	python scripts/run_profile.py --profile heavy/shared-dev

run-heavy-dedicated:
	python scripts/run_profile.py --profile heavy/dedicated

install-light:
	python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite

install-medium:
	python scripts/install_profile.py --profile medium --workspace .sim-workspaces/medium --overwrite

install-heavy:
	python scripts/install_profile.py --profile heavy --workspace .sim-workspaces/heavy --overwrite

install-heavy-shared:
	python scripts/install_profile.py --profile heavy/shared-dev --workspace .sim-workspaces/heavy-shared --overwrite

install-heavy-dedicated:
	python scripts/install_profile.py --profile heavy/dedicated --workspace .sim-workspaces/heavy-dedicated --overwrite

smoke-light:
	python scripts/http_smoke.py --system-config .sim-workspaces/light/config/system.json --base-url http://127.0.0.1:8099

smoke-medium:
	python scripts/http_smoke.py --system-config .sim-workspaces/medium/config/system.json --base-url http://127.0.0.1:8099

tail-light-logs:
	python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20

tail-medium-logs:
	python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --lines 20
