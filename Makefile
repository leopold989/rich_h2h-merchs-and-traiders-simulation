.PHONY: validate-light validate-medium validate-heavy schemas test run-light

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
	SIM_SYSTEM_CONFIG=examples/light/system.json rich-h2h-simulator
