from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from inventory.models import (
    Category,
    Incoming,
    Movement,
    Product,
    Sale,
    SalesReport,
    Stock,
    Warehouse,
    adjust_stock,
)


class InventoryModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Электроника")
        self.product = Product.objects.create(
            name="Телефон",
            category=self.category,
            purchase_price=Decimal("100.00"),
            selling_price=Decimal("150.00"),
        )
        self.warehouse_a = Warehouse.objects.create(name="Основной", location="Алмата")
        self.warehouse_b = Warehouse.objects.create(name="Резервный", location="Астана")

    def test_warehouse_profile_created(self):
        self.assertIsNotNone(self.warehouse_a.profile)
        self.assertIsNotNone(self.warehouse_b.profile)

    def test_adjust_stock_prevents_negative(self):
        with self.assertRaises(ValidationError):
            adjust_stock(self.warehouse_a, self.product, -1)

    def test_incoming_creates_stock(self):
        Incoming.objects.create(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=5,
        )
        stock = Stock.objects.get(warehouse=self.warehouse_a, product=self.product)
        self.assertEqual(stock.quantity, 5)

    def test_movement_requires_different_warehouses(self):
        with self.assertRaises(ValidationError):
            Movement(
                product=self.product,
                from_warehouse=self.warehouse_a,
                to_warehouse=self.warehouse_a,
                quantity=1,
            ).save()

    def test_sale_creates_report_and_updates_stock(self):
        adjust_stock(self.warehouse_a, self.product, 3)
        sale = Sale.objects.create(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=2,
            price=Decimal("0.00"),
            payment_method="cash",
        )
        sale.refresh_from_db()
        stock = Stock.objects.get(warehouse=self.warehouse_a, product=self.product)

        self.assertEqual(stock.quantity, 1)
        self.assertEqual(sale.price, self.product.selling_price)
        self.assertEqual(sale.total, self.product.selling_price * sale.quantity)
        self.assertTrue(SalesReport.objects.filter(sale=sale).exists())

    def test_sales_report_export_csv(self):
        adjust_stock(self.warehouse_a, self.product, 1)
        Sale.objects.create(
            product=self.product,
            warehouse=self.warehouse_a,
            quantity=1,
            payment_method="kaspi",
        )
        response = self.client.get(reverse("inventory:sales_report"), {"export": "csv"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("Дата,Склад,Товар,Количество,Цена,Сумма,Метод оплаты".encode(), response.content)
