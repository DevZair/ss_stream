from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.utils import timezone


def generate_warehouse_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self) -> str:
        return self.name


class Warehouse(models.Model):
    code = models.CharField(
        max_length=20,
        unique=True,
        default=generate_warehouse_code,
        editable=False,
    )
    name = models.CharField(max_length=150, unique=True)
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Склад"
        verbose_name_plural = "Склады"

    def __str__(self) -> str:
        return f"{self.name} ({self.location})"


class WarehouseProfile(models.Model):
    warehouse = models.OneToOneField(
        Warehouse, on_delete=models.CASCADE, related_name="profile"
    )
    manager_name = models.CharField(max_length=255, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    capacity = models.PositiveIntegerField(default=0)
    temperature_controlled = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Паспорт склада"
        verbose_name_plural = "Паспорта складов"

    def __str__(self) -> str:
        return f"Паспорт {self.warehouse.name}"


class Employee(models.Model):
    POSITION_CHOICES = [
        ("admin", "Админ"),
        ("storekeeper", "Кладовщик"),
        ("cashier", "Кассир"),
        ("accountant", "Бухгалтер"),
    ]
    ACTIVE = "active"
    BLOCKED = "blocked"
    STATUS_CHOICES = [
        (ACTIVE, "Активен"),
        (BLOCKED, "Заблокирован"),
    ]

    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    full_name = models.CharField(max_length=255)
    position = models.CharField(max_length=50, choices=POSITION_CHOICES, default="storekeeper")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="employees"
    )
    access_sections = models.ManyToManyField(
        "AccessSection",
        blank=True,
        related_name="employees",
    )

    class Meta:
        ordering = ("full_name",)
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self) -> str:
        return f"{self.full_name} — {self.get_position_display()}"


class AccessSection(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Раздел доступа"
        verbose_name_plural = "Разделы доступа"

    def __str__(self) -> str:
        return self.name


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
    date = models.DateField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Поступление"
        verbose_name_plural = "Поступления"

    def __str__(self) -> str:
        return f"{self.product} → {self.warehouse} (+{self.quantity})"

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.pk:
                prev = Incoming.objects.select_for_update().get(pk=self.pk)
                # вернуть старый приход
                adjust_stock(prev.warehouse, prev.product, -prev.quantity)
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
    date = models.DateField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-date",)
        verbose_name = "Перемещение"
        verbose_name_plural = "Перемещения"

    def clean(self):
        if self.from_warehouse == self.to_warehouse:
            raise ValidationError("Склады должны отличаться.")

    def save(self, *args, **kwargs):
        self.clean()
        with transaction.atomic():
            if self.pk:
                prev = Movement.objects.select_for_update().get(pk=self.pk)
                adjust_stock(prev.from_warehouse, prev.product, prev.quantity)
                adjust_stock(prev.to_warehouse, prev.product, -prev.quantity)
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
        ("mixed", "Смешанная"),
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
    cash_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    halyk_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    kaspi_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    payment_details = models.CharField(max_length=255, blank=True)
    seller = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_made",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

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

        # Распределение платежей
        if self.payment_method != "mixed":
            self.cash_amount = self.halyk_amount = self.kaspi_amount = Decimal("0.00")
            if self.payment_method == "cash":
                self.cash_amount = self.total
            elif self.payment_method == "halyk":
                self.halyk_amount = self.total
            elif self.payment_method == "kaspi":
                self.kaspi_amount = self.total
        else:
            paid_sum = sum([
                Decimal(self.cash_amount or 0),
                Decimal(self.halyk_amount or 0),
                Decimal(self.kaspi_amount or 0),
            ])
            if paid_sum != self.total:
                raise ValidationError("Сумма оплат должна совпадать с итогом продажи.")
            if paid_sum <= 0:
                raise ValidationError("Укажите суммы для смешанной оплаты.")

        with transaction.atomic():
            adjust_stock(self.warehouse, self.product, -self.quantity)
            super().save(*args, **kwargs)
            SalesReport.objects.create(sale=self)


class SalesReport(models.Model):
    SALE = "sale"
    MONTHLY = "monthly"
    REPORT_TYPES = [
        (SALE, "По продажам"),
        (MONTHLY, "Итоговый отчет"),
    ]
    DRAFT = "draft"
    FINAL = "final"
    STATUSES = [
        (DRAFT, "Черновик"),
        (FINAL, "Готов"),
    ]

    sale = models.ForeignKey(
        Sale, on_delete=models.CASCADE, related_name="reports"
    )
    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPES, default=SALE
    )
    status = models.CharField(max_length=20, choices=STATUSES, default=FINAL)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Отчет по продаже"
        verbose_name_plural = "Отчеты по продажам"

    def __str__(self) -> str:
        return f"Отчет #{self.pk} — продажа {self.sale_id} ({self.get_report_type_display()})"


class ActivityLog(models.Model):
    user = models.ForeignKey(
        get_user_model(), null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    employee = models.ForeignKey(
        "Employee", null=True, blank=True, on_delete=models.SET_NULL, related_name="activity_logs"
    )
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Активность сотрудника"
        verbose_name_plural = "Активности сотрудников"

    def __str__(self) -> str:
        return f"{self.action} ({self.created_at:%Y-%m-%d %H:%M})"


def log_activity(user, action: str, *, entity=None, details: str = ""):
    employee = getattr(user, "employee_profile", None)
    entity_type = entity.__class__.__name__ if entity else ""
    entity_id = entity.pk if entity and hasattr(entity, "pk") else None
    ActivityLog.objects.create(
        user=user if user.is_authenticated else None,
        employee=employee,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )


def _ensure_warehouse_profile(sender, instance, created, **kwargs):
    if created:
        WarehouseProfile.objects.create(warehouse=instance)


post_save.connect(_ensure_warehouse_profile, sender=Warehouse)
