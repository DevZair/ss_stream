-- Остатки по складам
SELECT w.name AS warehouse, p.name AS product, s.quantity
FROM inventory_stock s
JOIN inventory_warehouse w ON s.warehouse_id = w.id
JOIN inventory_product p ON s.product_id = p.id
ORDER BY w.name, p.name;

-- Продажи с разбивкой по оплатам и продавцу за период
SELECT DATE(s.created_at) AS day,
       w.name AS warehouse,
       p.name AS product,
       s.quantity,
       s.price,
       s.total,
       s.payment_method,
       s.cash_amount,
       s.halyk_amount,
       s.kaspi_amount,
       u.username AS seller
FROM inventory_sale s
JOIN inventory_product p ON s.product_id = p.id
JOIN inventory_warehouse w ON s.warehouse_id = w.id
LEFT JOIN auth_user u ON s.seller_id = u.id
WHERE s.created_at BETWEEN '2025-01-01' AND '2025-01-31'
ORDER BY day DESC;

-- Приходы/перемещения за последние 30 дней
SELECT 'incoming' AS op, i.date, w.name AS warehouse, p.name AS product, i.quantity
FROM inventory_incoming i
JOIN inventory_warehouse w ON i.warehouse_id = w.id
JOIN inventory_product p ON i.product_id = p.id
WHERE i.date >= DATE('now', '-30 day')
UNION ALL
SELECT 'movement', m.date, w_from.name, p.name, m.quantity
FROM inventory_movement m
JOIN inventory_warehouse w_from ON m.from_warehouse_id = w_from.id
JOIN inventory_product p ON m.product_id = p.id
WHERE m.date >= DATE('now', '-30 day');

-- Пользователь и доступные ему разделы (AccessSection)
SELECT u.username, a.slug
FROM auth_user u
JOIN inventory_employee e ON e.user_id = u.id
JOIN inventory_employee_access_sections ea ON ea.employee_id = e.id
JOIN inventory_accesssection a ON a.id = ea.accesssection_id;

-- Аудит действий (последние 50)
SELECT created_at, user_id, employee_id, action, entity_type, entity_id, details
FROM inventory_activitylog
ORDER BY created_at DESC
LIMIT 50;
