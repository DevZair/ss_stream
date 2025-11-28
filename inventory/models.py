from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name


class Warehouse(models.Model):
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255)

    class Meta:
        ordering = ("name",)
        verbose_name = "Склад"
        verbose_name_plural = "Склады"

    def __str__(self) -> str:
        return f"{self.name} ({self.location})"


class Employee(models.Model):
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=150)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="employees"
    )

    class Meta:
        ordering = ("full_name",)
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self) -> str:
        return f"{self.full_name} — {self.position}"


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    photo = models.ImageField(upload_to="products/", blank=True, null=True)

    class Meta:
        ordering = ("name",)
        unique_together = ("name", "category")
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self) -> str:
        return self.name


class Stock(models.Model):
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="stocks"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="stocks"
    )
    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("warehouse", "product")
        verbose_name = "Остаток"
        verbose_name_plural = "Остатки"

    def __str__(self) -> str:
        return f"{self.warehouse} - {self.product}: {self.quantity}"


def adjust_stock(warehouse: Warehouse, product: Product, delta: int) -> "Stock":
    """
    Atomically update stock and ensure quantity never becomes negative.
    """
    with transaction.atomic():
        stock, _ = Stock.objects.select_for_update().get_or_create(
            warehouse=warehouse,
            product=product,
            defaults={"quantity": 0},
        )
        if delta == 0:
            return stock
        new_quantity = stock.quantity + delta
        if new_quantity < 0:
            raise ValidationError("Недостаточно товара на складе.")
        stock.quantity = new_quantity
        stock.save()
        return stock


class Incoming(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="incoming"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="incoming"
    )
    quantity = models.PositiveIntegerField()
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Поступление"
        verbose_name_plural = "Поступления"

    def __str__(self) -> str:
        return f"{self.product} → {self.warehouse} (+{self.quantity})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Редактирование приходов запрещено.")
        with transaction.atomic():
            super().save(*args, **kwargs)
            adjust_stock(self.warehouse, self.product, self.quantity)


class Movement(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements"
    )
    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="movements_from",
    )
    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="movements_to",
    )
    quantity = models.PositiveIntegerField()
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Перемещение"
        verbose_name_plural = "Перемещения"

    def clean(self):
        if self.from_warehouse == self.to_warehouse:
            raise ValidationError("Склады должны отличаться.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.pk:
            raise ValidationError("Редактирование перемещений запрещено.")
        with transaction.atomic():
            super().save(*args, **kwargs)
            adjust_stock(self.from_warehouse, self.product, -self.quantity)
            adjust_stock(self.to_warehouse, self.product, self.quantity)

    def __str__(self) -> str:
        return f"{self.product} {self.from_warehouse} → {self.to_warehouse}"


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("kaspi", "Kaspi"),
        ("halyk", "Halyk"),
        ("cash", "Наличные"),
    ]

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="sales"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="sales"
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(
        max_digits=12, decimal_places=2, editable=False, default=Decimal("0.00")
    )
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHODS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Продажа"
        verbose_name_plural = "Продажи"

    def __str__(self) -> str:
        return f"{self.product} ({self.quantity})"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Редактирование продаж запрещено.")
        if not self.price:
            self.price = self.product.selling_price
        self.total = Decimal(self.price) * Decimal(self.quantity)
        with transaction.atomic():
            adjust_stock(self.warehouse, self.product, -self.quantity)
            super().save(*args, **kwargs)
            SalesReport.objects.create(sale=self)


class SalesReport(models.Model):
    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name="reports"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Отчет по продаже"
        verbose_name_plural = "Отчеты по продажам"

    def __str__(self) -> str:
        return f"Отчет #{self.pk} — продажа {self.sale_id}"
