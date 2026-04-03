# Patch 02 — merchant runner core

Этот патч добавляет первый рабочий merchant-side контур поверх Patch 01.

## Что реализовано

- запуск `merchant_jobs` как фоновых scheduler-задач;
- генерация `external_id` по шаблону;
- отправка `POST /api/h2h/order` в целевую dev-платформу;
- автоматическая подстановка `callback_url` из `public_base_url + merchants[].callback.path`;
- приём callback-ов мерчанта на сконфигурированные path;
- валидация callback `Access-Token`;
- runtime-state по jobs и созданным ордерам;
- логирование исходящих merchant-запросов и входящих callback-ов;
- hot reload с перестроением job-loop’ов.

## Что ещё не входит

- poll-after-create;
- `cancel`, `confirm_client`, `add_receipt`, `dispute`, `finish`;
- загрузка receipt fixtures в платформу.

Это приходит в Patch 03.
