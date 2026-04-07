# Установка системы

Этот документ описывает **установку самого сервиса**. Настройка конкретных merchant/trader сценариев вынесена отдельно.

## 1. Требования

Минимальный набор:

- Python 3.12+
- `pip`
- Git
- доступ к локальному каталогу для `config/`, `logs/`, `fixtures/`

Опционально:

- Docker + Docker Compose

## 2. Клонирование и структура проекта

После клонирования у тебя должны быть каталоги:

```text
src/
docs/
examples/
fixtures/
schemas/
scripts/
config/
logs/
```

Если `config/` пустой — это нормально. Для первого запуска его удобнее готовить через helper script.

## 3. Установка через venv

### Шаг 1. Создай окружение

```bash
python -m venv .venv
source .venv/bin/activate
```

### Шаг 2. Установи пакет

```bash
pip install -e .[dev]
```

### Шаг 3. Проверь, что package CLI доступен

```bash
python scripts/run_profile.py --help
rich-h2h-simulator-validate --help
```

Если CLI не найден — окружение активировано не тем shell’ом или `pip install -e .[dev]` не отработал.

## 4. Установка через Docker

### Шаг 1. Подготовь `.env`

```bash
cp .env.example .env
```

### Шаг 2. При необходимости подправь переменные

Обычно достаточно:

- `SIM_PORT`
- `SIM_CONFIG_DIR`
- `SIM_LOGS_DIR`
- `SIM_FIXTURES_DIR`

### Шаг 3. Собери образ

```bash
docker compose build
```

### Шаг 4. Запусти контейнер

```bash
docker compose up
```

Потом проверь:

```bash
curl http://127.0.0.1:8099/health
```

## 5. Что делать после установки

Дальше есть два рабочих пути:

### Путь A. Запуск прямо из `examples/`
Подходит для первого знакомства и локального smoke.

Смотри: [docs/quickstart/light-e2e.md](../quickstart/light-e2e.md)

### Путь B. Подготовить отдельный workspace
Подходит для реальной работы с dev-стендом, когда не хочется править `examples/`.

```bash
python scripts/install_profile.py --profile light --workspace .sim-workspaces/light --overwrite
```

Дальше смотри: [docs/install/system-setup.md](system-setup.md)
