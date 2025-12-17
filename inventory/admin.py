from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Employee,
    Incoming,
    Movement,
    AccessSection,
    ActivityLog,
    Product,
    Sale,
    SaleItem,
    SalesReport,
    Stock,
    Warehouse,
    WarehouseProfile,
)


class EmployeeInline(admin.TabularInline):
    model = Employee
    extra = 0
    fields = ("full_name", "position")


class WarehouseProfileInline(admin.StackedInline):
    model = WarehouseProfile
    extra = 0
    max_num = 1
    can_delete = False


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


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "quantity", "price", "total")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location", "created_at")
    list_filter = ("location",)
    search_fields = ("code", "name", "location")
    inlines = (WarehouseProfileInline, EmployeeInline, WarehouseStockInline)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "position", "status", "warehouse", "user")
    list_filter = ("warehouse", "status", "position")
    search_fields = ("full_name", "position", "user__username")
    filter_horizontal = ("access_sections",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "barcode", "category", "purchase_price", "selling_price", "has_photo")
    list_filter = ("category",)
    search_fields = ("name", "barcode")
    readonly_fields = ("photo_preview",)
    inlines = (ProductStockInline,)
    fieldsets = (
        (None, {"fields": ("name", "barcode", "category")}),
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
    list_display = ("receipt_number", "warehouse", "total", "payment_method", "seller", "created_at")
    list_filter = ("warehouse", "payment_method", "created_at", "items__product__category")
    date_hierarchy = "created_at"
    search_fields = ("items__product__name", "seller__username")
    readonly_fields = ("total", "receipt_number")
    inlines = (SaleItemInline,)


@admin.register(SalesReport)
class SalesReportAdmin(admin.ModelAdmin):
    list_display = ("sale", "report_type", "status", "created_at")
    date_hierarchy = "created_at"
    search_fields = ("sale__product__name",)


@admin.register(AccessSection)
class AccessSectionAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    search_fields = ("slug", "name")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("action", "user", "employee", "entity_type", "entity_id", "created_at")
    list_filter = ("entity_type", "created_at")
    search_fields = ("action", "details", "user__username", "employee__full_name")
