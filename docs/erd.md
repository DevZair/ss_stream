# ERD (текстовое описание)

- `Category` (id, name*, description, is_active, created_at)
  - 1:N с `Product`
- `Warehouse` (id, code*, name*, location, created_at)
  - 1:N с `Employee`, `Stock`, `Incoming`, `Movement` (как from/to), `Sale`
  - 1:1 с `WarehouseProfile`
- `WarehouseProfile` (id, warehouse!, manager_name, contact_phone, capacity, temperature_controlled)
  - 1:1 паспорт склада
- `Employee` (id, full_name, position, warehouse!)
  - принадлежит складу (1:N)
- `Product` (id, name, category!, purchase_price, selling_price, photo)
  - 1:N с `Incoming`, `Movement`, `Sale`
  - M:N со складами через `Stock`
- `Stock` (id, warehouse!, product!, quantity)
  - связывает `Warehouse` и `Product` (Many:Many) + количество
- `Incoming` (id, product!, warehouse!, quantity, date)
  - фиксирует приход и обновляет `Stock`
- `Movement` (id, product!, from_warehouse!, to_warehouse!, quantity, date)
  - перемещение между складами, валидация на разные склады
- `Sale` (id, product!, warehouse!, quantity, price, total, payment_method, cash_amount, halyk_amount, kaspi_amount, payment_details, seller?, created_at)
  - уменьшает `Stock`, создает `SalesReport`, фиксирует способ оплаты и продавца
- `SalesReport` (id, sale!, report_type, status, notes, created_at)
  - фиксирует факт продажи и тип отчета
- `AccessSection` (id, slug*, name)
  - справочник прав доступа внутри системы (sales, orders, reports, warehouses и т.д.)
- `Employee.access_sections` (M2M через `inventory_employee_access_sections`)
  - определяет, какие разделы доступны сотруднику
- `ActivityLog` (id, user?, employee?, action, entity_type, entity_id, details, created_at)
  - аудит действий пользователя/сотрудника (продажи, приходы, перемещения)

Ключи и уникальность:
- PK на каждой таблице (BigAutoField).
- `Warehouse.code` и `Warehouse.name` уникальны; `Category.name` уникален; `Product` уникален в паре (name, category); `Stock` уникален по (warehouse, product).
- Связи: 1:1 (`Warehouse`–`WarehouseProfile`), 1:N (склад → сотрудники, остатки, приходы, перемещения, продажи), M:N (склады ↔ товары через `Stock`; сотрудники ↔ доступы через `AccessSection`).
