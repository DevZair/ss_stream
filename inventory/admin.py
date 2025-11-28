from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Employee,
    Incoming,
    Movement,
    Product,
    Sale,
    SalesReport,
    Stock,
    Warehouse,
)


class EmployeeInline(admin.TabularInline):
    model = Employee
    extra = 0
    fields = ("full_name", "position")


class WarehouseStockInline(admin.TabularInline):
    model = Stock
    fk_name = "warehouse"
    extra = 0
    readonly_fields = ("product", "quantity")
    can_delete = False


class ProductStockInline(admin.TabularInline):
    model = Stock
    fk_name = "product"
    extra = 0
    readonly_fields = ("warehouse", "quantity")
    can_delete = False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "location")
    list_filter = ("location",)
    search_fields = ("name", "location")
    inlines = (EmployeeInline, WarehouseStockInline)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "warehouse")
    list_filter = ("warehouse",)
    search_fields = ("full_name", "position")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "purchase_price", "selling_price", "has_photo")
    list_filter = ("category",)
    search_fields = ("name",)
    readonly_fields = ("photo_preview",)
    inlines = (ProductStockInline,)
    fieldsets = (
        (None, {"fields": ("name", "category")}),
        ("Ценообразование", {"fields": ("purchase_price", "selling_price")}),
        ("Фото", {"fields": ("photo", "photo_preview")}),
    )

    @admin.display(description="Фото", boolean=True)
    def has_photo(self, obj):
        return bool(obj.photo)

    @admin.display(description="Предпросмотр")
    def photo_preview(self, obj):
        if not obj.photo:
            return "—"
        return format_html('<img src="{}" style="max-height: 120px;" />', obj.photo.url)


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ("warehouse", "product", "quantity")
    list_filter = ("warehouse", "product__category")
    search_fields = ("warehouse__name", "product__name")


@admin.register(Incoming)
class IncomingAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "date")
    list_filter = ("warehouse", "product__category", "date")
    date_hierarchy = "date"
    search_fields = ("product__name", "warehouse__name")


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "from_warehouse",
        "to_warehouse",
        "quantity",
        "date",
    )
    list_filter = ("from_warehouse", "to_warehouse", "product__category", "date")
    date_hierarchy = "date"
    search_fields = ("product__name",)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "warehouse", "quantity", "price", "total", "payment_method", "created_at")
    list_filter = ("warehouse", "product__category", "payment_method", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("product__name",)
    readonly_fields = ("total",)


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ("sale", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("sale__product__name",)
