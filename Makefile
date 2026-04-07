.PHONY: \
	validate-light validate-medium validate-heavy schemas test \
	run-light run-medium run-heavy \
	install-light install-medium install-heavy \
	smoke-light smoke-medium \
	tail-light-logs tail-medium-logs

validate-light:
	python scripts/validate_config.py --system-config examples/light/system.json --dump-state

validate-medium:
	python scripts/validate_config.py --system-config examples/medium/system.json

validate-heavy:
	python scripts/validate_config.py --system-config examples/heavy/system.json

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

install-light:
	python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite

install-medium:
	python scripts/install_profile.py --profile medium --workspace .sim-workspaces/medium --overwrite

install-heavy:
	python scripts/install_profile.py --profile heavy --workspace .sim-workspaces/heavy --overwrite

smoke-light:
	python scripts/http_smoke.py --system-config .sim-workspaces/light/config/system.json --base-url http://127.0.0.1:8099

smoke-medium:
	python scripts/http_smoke.py --system-config .sim-workspaces/medium/config/system.json --base-url http://127.0.0.1:8099

tail-light-logs:
	python scripts/tail_logs.py --system-config .sim-workspaces/light/config/system.json --lines 20

tail-medium-logs:
	python scripts/tail_logs.py --system-config .sim-workspaces/medium/config/system.json --lines 20
