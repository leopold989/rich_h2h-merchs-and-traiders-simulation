# Установка системы

## Что устанавливаем на Patch 01

На этом этапе поднимается **каркас сервиса**, а не полноценный merchant/trader runtime.

## Требования

- Python 3.12+
- pip
- Docker + docker compose — опционально
- доступ к локальному файловому каталогу для конфигов и логов

## Вариант A — локально через venv

### 1. Создай виртуальное окружение

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Установи пакет

```bash
pip install -e .[dev]
```

### 3. Проверь, что структура проекта на месте

Нужны каталоги:

```text
config/
examples/
fixtures/
logs/
schemas/
```

### 4. Провалидация конфигов

```bash
python scripts/validate_config.py --system-config examples/light/system.json --dump-state
```

### 5. Запусти сервис

```bash
SIM_SYSTEM_CONFIG=examples/light/system.json rich-h2h-simulator
```

## Вариант B — через Docker

### 1. Собери образ

```bash
docker compose build
```

### 2. Проверь каталоги volume mount

- `./config`
- `./logs`
- `./fixtures`

### 3. Запусти контейнер

```bash
docker compose up
```

## После установки

Следующий шаг — [docs/install/system-setup.md](system-setup.md).
