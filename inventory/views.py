import csv

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import (
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
    EmployeeForm,
    IncomingForm,
    MovementForm,
    ProductForm,
    SaleForm,
    SalesReportFilterForm,
    WarehouseForm,
)
from .models import Employee, Product, Sale, Stock, Warehouse


def product_list(request):
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


def warehouse_list(request):
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
    return render(
        request,
        "inventory/warehouse_list.html",
        {"warehouses": warehouses},
    )


def warehouse_create(request):
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


def incoming_create(request):
    return _handle_stock_operation(
        request=request,
        form_class=IncomingForm,
        template="inventory/operations_incoming.html",
        success_url=reverse("inventory:stock_list"),
        title="Приход товара",
        success_message="Поступление сохранено.",
    )


def movement_create(request):
    return _handle_stock_operation(
        request=request,
        form_class=MovementForm,
        template="inventory/operations_movement.html",
        success_url=reverse("inventory:stock_list"),
        title="Перемещение товара",
        success_message="Перемещение сохранено.",
    )


def sale_create(request):
    return _handle_stock_operation(
        request=request,
        form_class=SaleForm,
        template="inventory/operations_sale.html",
        success_url=reverse("inventory:stock_list"),
        title="Продажа товара",
        success_message="Продажа проведена.",
    )


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
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, success_message)
                return redirect(success_url)
    else:
        form = form_class()
    return render(
        request,
        template,
        {
            "form": form,
            "title": title,
            "submit_label": "Сохранить",
            **(extra_context or {}),
        },
    )


def stock_list(request):
    stocks = (
        Stock.objects.select_related("warehouse", "product", "product__category")
        .order_by("warehouse__name", "product__name")
    )
    return render(
        request,
        "inventory/stock_list.html",
        {"stocks": stocks},
    )


def sales_report(request):
    sales = (
        Sale.objects.select_related("product", "warehouse")
        .order_by("-created_at")
    )
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
