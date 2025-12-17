## Запуск
1. Установить зависимости и настроить БД (по умолчанию PostgreSQL через `DJANGO_DB_ENGINE=postgres`. Для SQLite локально: `DJANGO_DB_ENGINE=sqlite`).
2. Применить миграции и создать суперпользователя/роли:
   ```bash
   ./scripts/run_migrations.sh
   python3 manage.py createsu
   python3 manage.py setup_roles
   ```
3. Запустить сервер: `python3 manage.py runserver`.

## Автоматизация и резервные копии
- Миграции: `scripts/run_migrations.sh`.
- Бэкап: `scripts/backup_db.sh` (Postgres pg_dump→gzip или gzip SQLite в `backups/`).
- Восстановление: `scripts/restore_db.sh backups/<dump>.sql.gz`.
- Проверка восстановления: `scripts/backup_and_restore_check.sh` — делает бэкап и проверяет, что восстановление в тестовую БД/файл проходит (требуются `psql` для Postgres или `sqlite3` для SQLite).
- Сброс демо-окружения: `scripts/demo_reset.sh` — восстанавливает из эталонного бэкапа `backups/demo_seed.sql.gz` (Postgres) или `backups/demo_seed.sqlite.gz` (SQLite). Создайте эталонный бэкап один раз командой `./scripts/backup_db.sh` и переименуйте файл.
- Политика бэкапов: `docs/backup_policy.md`.

## Модель данных и связи
- ERD: `docs/erd.md` (>=5 таблиц, ключи, уникальные поля, связи 1:1, 1:N, M:N).
- Уникальный идентификатор склада: `Warehouse.code`; уникальные категории; товары уникальны внутри категории; остатки уникальны по складу/товару.
- One-to-One: `WarehouseProfile`; Many-to-Many: склады ↔ товары через `Stock`.

## Отчеты и SQL
- Отчет по продажам с фильтрами, итогами и экспортом CSV (`/reports/sales/`).
- Примеры SQL-запросов: `docs/sql_examples.sql` (остатки, продажи, приход/перемещения, доступы, аудит).

## Безопасность и роли
- Команда `python3 manage.py setup_roles` создает группы: Администратор (все права), Менеджер склада (add/change/view), Оператор (add/view на операции и остатки).
- Создание суперпользователя: `python3 manage.py createsu` (читается из переменных окружения).

## Тесты
- Юнит-тесты критических операций: `python3 manage.py test inventory.tests` (валидация остатков, движение, продажа, отчет CSV).
- Для SQLite-тестов установить `DJANGO_DB_ENGINE=sqlite`.

## Отчет и защита
- Шаблон отчета: `docs/report_outline.md`; презентация: `docs/presentation_outline.md`.
- Добавить скриншоты UI/БД в отчет и отметить прохождение тестов и бэкапов.
