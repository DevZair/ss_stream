-- Простой выбор остатков по складу
SELECT w.name AS warehouse, p.name AS product, s.quantity
FROM inventory_stock s
JOIN inventory_warehouse w ON s.warehouse_id = w.id
JOIN inventory_product p ON s.product_id = p.id
ORDER BY w.name, p.name;

-- Сводка продаж по способу оплаты и периоду (GROUP BY)
SELECT DATE(s.created_at) AS day,
       s.payment_method,
       SUM(s.quantity) AS total_qty,
       SUM(s.total) AS total_amount
FROM inventory_sale s
WHERE s.created_at BETWEEN '2025-01-01' AND '2025-01-31'
GROUP BY DATE(s.created_at), s.payment_method
ORDER BY day DESC;

-- Подзапрос для поиска товаров без остатка
SELECT p.id, p.name
FROM inventory_product p
WHERE NOT EXISTS (
    SELECT 1 FROM inventory_stock s WHERE s.product_id = p.id AND s.quantity > 0
);

-- Журнал перемещений с указанием типа связи (JOIN двух ссылок на один справочник)
SELECT m.date,
       p.name AS product,
       w_from.name AS from_wh,
       w_to.name AS to_wh,
       m.quantity
FROM inventory_movement m
JOIN inventory_product p ON m.product_id = p.id
JOIN inventory_warehouse w_from ON m.from_warehouse_id = w_from.id
JOIN inventory_warehouse w_to ON m.to_warehouse_id = w_to.id
ORDER BY m.date DESC
LIMIT 50;

-- Прибыль по категориям (JOIN + GROUP BY)
SELECT c.name AS category,
       SUM(s.total) AS revenue,
       SUM((s.price - p.purchase_price) * s.quantity) AS profit
FROM inventory_sale s
JOIN inventory_product p ON s.product_id = p.id
JOIN inventory_category c ON p.category_id = c.id
GROUP BY c.name
HAVING SUM(s.total) > 0
ORDER BY profit DESC;
