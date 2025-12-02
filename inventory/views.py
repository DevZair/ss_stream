import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Prefetch,
    Q,
    Value,
    Sum,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    CategoryForm,
    EmployeeForm,
    EmployeeUpdateForm,
    IncomingForm,
    MovementForm,
    ProductForm,
    SaleForm,
    SalesReportFilterForm,
    WarehouseForm,
)
from .models import Category, Employee, Product, Sale, Stock, Warehouse
from .models import log_activity


def product_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    employee_wh = _user_warehouse(request.user)
    products = (
        Product.objects.select_related("category")
        .annotate(total_stock=Coalesce(Sum("stocks__quantity"), 0))
        .order_by("name")
    )
    return render(
        request,
        "inventory/product_list.html",
        {"products": products},
    )


def product_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Товар добавлен.")
            return redirect("inventory:product_list")
    else:
        form = ProductForm()
    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "title": "Добавить товар", "submit_label": "Сохранить"},
    )


def category_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "categories")
    categories = Category.objects.annotate(products_count=Count("products")).order_by("name")
    return render(
        request,
        "inventory/category_list.html",
        {"categories": categories},
    )


def category_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Категория добавлена.")
            return redirect("inventory:category_list")
    else:
        form = CategoryForm()
    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "title": "Добавить категорию", "submit_label": "Сохранить"},
    )


def warehouse_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "warehouses")
    employee_wh = _user_warehouse(request.user)
    warehouses = (
        Warehouse.objects.annotate(total_stock=Coalesce(Sum("stocks__quantity"), 0))
        .prefetch_related(
            Prefetch("employees", queryset=Employee.objects.order_by("full_name")),
            Prefetch(
                "stocks",
                queryset=Stock.objects.select_related("product").order_by("product__name"),
            ),
        )
        .order_by("name")
    )
    if employee_wh and not request.user.is_superuser:
        warehouses = warehouses.filter(pk=employee_wh.pk)
    return render(
        request,
        "inventory/warehouse_list.html",
        {"warehouses": warehouses},
    )


def warehouse_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Склад добавлен.")
            return redirect("inventory:warehouse_list")
    else:
        form = WarehouseForm()
    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "title": "Добавить склад", "submit_label": "Сохранить"},
    )


def employee_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    if request.method == "POST":
        form = EmployeeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Сотрудник добавлен.")
            return redirect("inventory:warehouse_list")
    else:
        form = EmployeeForm()
    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "title": "Добавить сотрудника", "submit_label": "Сохранить"},
    )


def employee_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "employees")
    employee_wh = _user_warehouse(request.user)
    employees = (
        Employee.objects.select_related("warehouse", "user")
        .prefetch_related("access_sections")
        .order_by("full_name")
    )
    if employee_wh and not request.user.is_superuser:
        employees = employees.filter(warehouse=employee_wh)
    return render(
        request,
        "inventory/employee_list.html",
        {"employees": employees},
    )


def orders_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "orders")
    employee_wh = _user_warehouse(request.user)
    orders = (
        Sale.objects.select_related("product", "warehouse", "seller")
        .order_by("-created_at")
    )
    if employee_wh and not request.user.is_superuser:
        orders = orders.filter(warehouse=employee_wh)
    return render(
        request,
        "inventory/orders_list.html",
        {"orders": orders},
    )


def logs_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "logs")
    from .models import ActivityLog

    logs = ActivityLog.objects.select_related("user", "employee").order_by("-created_at")
    employee_wh = _user_warehouse(request.user)
    if employee_wh and not request.user.is_superuser:
        logs = logs.filter(employee__warehouse=employee_wh)
    return render(
        request,
        "inventory/logs_list.html",
        {"logs": logs},
    )


def pos_dashboard(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "sales")
    employee_wh = _user_warehouse(request.user)
    products = (
        Product.objects.select_related("category")
        .annotate(total_stock=Coalesce(Sum("stocks__quantity"), 0))
        .order_by("name")
    )
    wh_stock = {}
    if employee_wh:
        wh_stock = dict(
            Stock.objects.filter(warehouse=employee_wh)
            .values_list("product_id")
            .annotate(qty=Sum("quantity"))
        )

    keypad_rows = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["000", "0", "<-"]
    ]

    price_map = {str(p.id): str(p.selling_price) for p in products}
    stock_map = {
        str(p.id): {
            "local": wh_stock.get(p.id, 0) if isinstance(wh_stock, dict) else 0,
            "total": p.total_stock,
        }
        for p in products
    }

    if request.method == "POST":
        form = SaleForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                sale = form.save(commit=False)
                sale.seller = request.user
                # если смешанная и суммы не совпадают — выставляем всё в наличные
                if sale.payment_method == "mixed":
                    paid_sum = (sale.cash_amount or 0) + (sale.halyk_amount or 0) + (sale.kaspi_amount or 0)
                    if paid_sum != sale.total:
                        sale.cash_amount = sale.total
                        sale.halyk_amount = 0
                        sale.kaspi_amount = 0
                sale.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                log_activity(
                    request.user,
                    "Продажа (касса)",
                    entity=sale,
                    details=f"Товар: {sale.product}, склад: {sale.warehouse}, сумма: {sale.total}",
                )
                messages.success(request, "Продажа проведена через кассу.")
                return redirect("inventory:orders_list")
    else:
        form = SaleForm(user=request.user)

    return render(
        request,
        "inventory/pos.html",
        {
            "form": form,
            "products": products,
            "warehouse": employee_wh,
            "warehouse_stock": wh_stock,
            "keypad_rows": keypad_rows,
            "price_map": price_map,
            "stock_map": stock_map,
        },
    )


def employee_update(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "employees")
    employee = get_object_or_404(Employee.objects.select_related("user"), pk=pk)
    employee_wh = _user_warehouse(request.user)
    if employee_wh and not request.user.is_superuser and employee.warehouse_id != employee_wh.id:
        messages.error(request, "Нет доступа к этому сотруднику.")
        return redirect("inventory:employee_list")
    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "Сотрудник обновлен.")
            return redirect("inventory:employee_list")
    else:
        form = EmployeeUpdateForm(instance=employee)
    return render(
        request,
        "inventory/product_form.html",
        {"form": form, "title": "Редактировать сотрудника", "submit_label": "Сохранить"},
    )


def incoming_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "incoming")
    return _handle_stock_operation(
        request=request,
        form_class=IncomingForm,
        template="inventory/operations_incoming.html",
        success_url=reverse("inventory:stock_list"),
        title="Приход товара",
        success_message="Поступление сохранено.",
    )


def incoming_edit(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "incoming")
    incoming = get_object_or_404(Incoming, pk=pk)
    if request.method == "POST":
        form = IncomingForm(request.POST, instance=incoming, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, "Приход обновлен.")
                return redirect("inventory:stock_list")
    else:
        form = IncomingForm(instance=incoming, user=request.user)
    return render(
        request,
        "inventory/operations_incoming.html",
        {
            "form": form,
            "title": "Изменить приход",
            "submit_label": "Сохранить",
        },
    )


def movement_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "movements")
    return _handle_stock_operation(
        request=request,
        form_class=MovementForm,
        template="inventory/operations_movement.html",
        success_url=reverse("inventory:stock_list"),
        title="Перемещение товара",
        success_message="Перемещение сохранено.",
    )


def sale_create(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "sales")
    return redirect("inventory:pos")


def product_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "products")
    product = get_object_or_404(Product, pk=pk)
    try:
        product.delete()
        messages.success(request, "Товар удален.")
    except ProtectedError:
        messages.error(request, "Нельзя удалить: есть связанные операции/продажи.")
    return redirect("inventory:product_list")


def _handle_stock_operation(
    *,
    request,
    form_class,
    template: str,
    success_url: str,
    title: str,
    success_message: str,
    extra_context: dict | None = None,
):
    employee_wh = _user_warehouse(request.user)
    if employee_wh is None and not request.user.is_superuser:
        messages.error(request, "Нет склада, закрепленного за вашим аккаунтом.")
        return redirect("inventory:product_list")

    if request.method == "POST":
        form = form_class(request.POST, user=request.user)
        if form.is_valid():
            try:
                # Проставляем продавца для продаж
                if isinstance(form, SaleForm):
                    form.instance.seller = request.user
                instance = form.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                _log_operation(request.user, instance)
                messages.success(request, success_message)
                return redirect(success_url)
    else:
        form = form_class(user=request.user)

    context = {
        "form": form,
        "title": title,
        "submit_label": "Сохранить",
        **(extra_context or {}),
    }

    # Передаем цены продуктов для автоподстановки в форме продажи
    if isinstance(form, SaleForm):
        qs = form.fields["product"].queryset
        context["price_map"] = {str(p.id): str(p.selling_price) for p in qs}
    return render(
        request,
        template,
        context,
    )


def stock_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "stocks")
    employee_wh = _user_warehouse(request.user)
    stocks = (
        Stock.objects.select_related("warehouse", "product", "product__category")
        .order_by("warehouse__name", "product__name")
    )
    if employee_wh and not request.user.is_superuser:
        stocks = stocks.filter(warehouse=employee_wh)
    return render(
        request,
        "inventory/stock_list.html",
        {"stocks": stocks},
    )


def sales_report(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "reports")
    employee_wh = _user_warehouse(request.user)
    sales = (
        Sale.objects.select_related("product", "warehouse")
        .order_by("-created_at")
    )
    if employee_wh and not request.user.is_superuser:
        sales = sales.filter(warehouse=employee_wh)
    form = SalesReportFilterForm(request.GET or None)
    start_date = end_date = None
    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        if start_date:
            sales = sales.filter(created_at__date__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__date__lte=end_date)
    profit_expression = ExpressionWrapper(
        (F("price") - F("product__purchase_price")) * F("quantity"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    sales = sales.annotate(profit=profit_expression)
    sales_count = sales.count()

    zero_decimal = Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))
    raw_stats = sales.aggregate(
        total_qty=Coalesce(Sum("quantity"), 0),
        total_amount=Coalesce(Sum("total"), zero_decimal),
        total_profit=Coalesce(Sum("profit"), zero_decimal),
        kaspi_total=Coalesce(
            Sum("total", filter=Q(payment_method="kaspi")), zero_decimal
        ),
        halyk_total=Coalesce(
            Sum("total", filter=Q(payment_method="halyk")), zero_decimal
        ),
        cash_total=Coalesce(
            Sum("total", filter=Q(payment_method="cash")), zero_decimal
        ),
        mixed_total=Coalesce(
            Sum("total", filter=Q(payment_method="mixed")), zero_decimal
        ),
    )
    stats = {key: raw_stats.get(key, 0) or 0 for key in raw_stats}

    if request.GET.get("export") == "csv":
        return _export_sales_csv(sales)

    query_params = request.GET.copy()
    query_params["export"] = "csv"
    export_url = f"{reverse('inventory:sales_report')}?{query_params.urlencode()}"

    return render(
        request,
        "inventory/report_sales.html",
        {
            "form": form,
            "sales": sales,
            "stats": stats,
            "start_date": start_date,
            "end_date": end_date,
            "sales_count": sales_count,
            "export_url": export_url,
            "employee_wh": employee_wh,
        },
    )


def _export_sales_csv(sales_queryset):
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="sales_{timestamp}.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ["Дата", "Склад", "Товар", "Количество", "Цена", "Сумма", "Метод оплаты"]
    )
    for sale in sales_queryset:
        sale_date = sale.created_at
        if timezone.is_aware(sale_date):
            sale_date_display = timezone.localtime(sale_date).strftime("%Y-%m-%d %H:%M")
        else:
            sale_date_display = sale_date.strftime("%Y-%m-%d %H:%M")
        writer.writerow([
            sale_date_display,
            sale.warehouse.name,
            sale.product.name,
            sale.quantity,
            sale.price,
            sale.total,
            sale.get_payment_method_display(),
        ])
    return response


def _user_warehouse(user):
    if getattr(user, "is_superuser", False):
        return None
    employee = getattr(user, "employee_profile", None)
    return getattr(employee, "warehouse", None)


def _require_access(user, slug: str):
    if getattr(user, "is_superuser", False):
        return
    employee = getattr(user, "employee_profile", None)
    if not employee:
        raise PermissionDenied("Недостаточно прав.")
    if not employee.access_sections.filter(slug=slug).exists():
        raise PermissionDenied("Недостаточно прав.")


def _log_operation(user, instance):
    try:
        action = instance._meta.verbose_name.capitalize()
        log_activity(
            user,
            f"{action} создано",
            entity=instance,
            details=str(instance),
        )
    except Exception:
        pass
