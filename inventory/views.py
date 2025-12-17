import csv
import base64
from decimal import Decimal

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
    Max,
)
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics import renderPM
from reportlab.lib.units import mm

from .forms import (
    CategoryForm,
    EmployeeForm,
    EmployeeUpdateForm,
    IncomingForm,
    MovementForm,
    ProductForm,
    SalePaymentForm,
    SaleItemFormSet,
    SalesReportFilterForm,
    WarehouseForm,
)
from .models import (
    Category,
    Employee,
    Product,
    Sale,
    SaleItem,
    SalesReport,
    Stock,
    Warehouse,
    Incoming,
    Movement,
)
from .models import adjust_stock, log_activity


def _barcode_data_uri(code: str | None) -> str | None:
    """
    Build a base64 PNG barcode data URI for given code using Code128 (без изменения строки).
    """
    if not code:
        return None
    value = str(code).strip()
    if not value:
        return None
    try:
        drawing = createBarcodeDrawing(
            "Code128",
            value=value,
            barHeight=22 * mm,
            barWidth=0.34 * mm,
            humanReadable=True,
        )
        png_bytes = renderPM.drawToString(drawing, fmt="PNG")
    except Exception:
        return None
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode()}"


def _ensure_ean13(value: str) -> str:
    """
    Deprecated: no longer used (оставлено для совместимости).
    """
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits


def product_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    employee_wh = _user_warehouse(request.user)
    products = (
        Product.objects.select_related("category")
        .annotate(total_stock=Coalesce(Sum("stocks__quantity"), 0))
        .order_by("name")
    )
    next_receipt = (Sale.objects.order_by("-id").values_list("id", flat=True).first() or 0) + 1
    categories = Category.objects.order_by("name")
    categories = Category.objects.order_by("name")
    categories = Category.objects.order_by("name")
    categories = Category.objects.order_by("name")
    categories = Category.objects.order_by("name")
    return render(
        request,
        "inventory/product_list.html",
        {"products": products},
    )


def product_barcode(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    barcode_value = (product.barcode or "").strip()
    barcode_uri = _barcode_data_uri(barcode_value) if barcode_value else None
    return render(
        request,
        "inventory/product_barcode.html",
        {
            "product": product,
            "barcode_data": barcode_uri,
            "barcode_value": barcode_value,
        },
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
        Sale.objects.select_related("warehouse", "seller")
        .prefetch_related("items__product")
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
    last_warehouse_id = None
    products = (
        Product.objects.select_related("category")
        .annotate(total_stock=Coalesce(Sum("stocks__quantity"), 0))
        .order_by("name")
    )
    categories = Category.objects.order_by("name")

    keypad_rows = [
        ["1", "2", "3"],
        ["4", "5", "6"],
        ["7", "8", "9"],
        ["000", "0", "<-"]
    ]
    last_receipt = Sale.objects.aggregate(last=Max("receipt_number")).get("last") or 0
    next_receipt = last_receipt + 1

    if request.method == "POST":
        payment_form = SalePaymentForm(request.POST, user=request.user)
        items_formset = SaleItemFormSet(request.POST, prefix="items")
        if payment_form.is_valid() and items_formset.is_valid():
            items = []
            total = Decimal("0.00")
            total_qty = 0
            for item_form in items_formset:
                if item_form.cleaned_data.get("DELETE"):
                    continue
                product = item_form.cleaned_data.get("product")
                quantity = item_form.cleaned_data.get("quantity") or 0
                price = item_form.cleaned_data.get("price") or Decimal("0.00")
                if not product or quantity <= 0:
                    continue
                line_total = Decimal(price) * Decimal(quantity)
                items.append(
                    {"product": product, "quantity": quantity, "price": price, "total": line_total}
                )
                total += line_total
                total_qty += quantity
            if not items:
                payment_form.add_error(None, "Добавьте хотя бы один товар")
            else:
                payment_form.normalize_payments(total)
                try:
                    with transaction.atomic():
                        sale = payment_form.save(commit=False)
                        sale.seller = request.user
                        last_receipt_locked = (
                            Sale.objects.select_for_update()
                            .order_by("-receipt_number")
                            .values_list("receipt_number", flat=True)
                            .first()
                            or 0
                        )
                        sale.receipt_number = last_receipt_locked + 1
                        sale.total = total
                        sale.quantity = total_qty
                        sale.price = total
                        sale.product = items[0]["product"]
                        sale.save()
                        for item in items:
                            SaleItem.objects.create(
                                sale=sale,
                                product=item["product"],
                                quantity=item["quantity"],
                                price=item["price"],
                                total=item["total"],
                            )
                        SalesReport.objects.create(sale=sale)
                except ValidationError as exc:
                    payment_form.add_error(None, exc.messages[0])
                else:
                    item_details = "; ".join(
                        f"{it['product']} x{it['quantity']} @ {it['price']}"
                        for it in items
                    )
                    log_activity(
                        request.user,
                        "Продажа (касса)",
                        entity=sale,
                        details=f"{item_details}; склад: {sale.warehouse}, сумма: {sale.total}",
                    )
                    request.session["pos_last_wh"] = sale.warehouse_id
                    messages.success(request, f"Продажа проведена через кассу. Чек №{sale.receipt_number}.")
                    return redirect("inventory:pos")
    else:
        last_warehouse_id = request.session.pop("pos_last_wh", None)
        payment_form = SalePaymentForm(user=request.user)
        if last_warehouse_id:
            wh_qs = payment_form.fields["warehouse"].queryset
            if wh_qs.filter(id=last_warehouse_id).exists():
                payment_form.initial["warehouse"] = last_warehouse_id
                payment_form.fields["warehouse"].initial = last_warehouse_id
        items_formset = SaleItemFormSet(prefix="items", initial=[])

    available_wh_ids = list(
        payment_form.fields["warehouse"].queryset.values_list("id", flat=True)
    )
    stocks_qs = Stock.objects.filter(warehouse_id__in=available_wh_ids)

    stock_map = {
        str(p.id): {
            "total": p.total_stock,
            "warehouses": {},
        }
        for p in products
    }
    for entry in stocks_qs.values("product_id", "warehouse_id").annotate(qty=Sum("quantity")):
        pid = str(entry["product_id"])
        wid = str(entry["warehouse_id"])
        stock_map.setdefault(pid, {"total": 0, "warehouses": {}})
        stock_map[pid]["warehouses"][wid] = entry["qty"] or 0

    warehouse_stock_counts = {str(wid): 0 for wid in available_wh_ids}
    for wid, cnt in stocks_qs.values_list("warehouse_id").annotate(cnt=Count("id")):
        warehouse_stock_counts[str(wid)] = cnt or 0

    price_map = {str(p.id): str(p.selling_price) for p in products}
    barcode_map = {p.barcode: str(p.id) for p in products if p.barcode}
    products_payload = [
        {
            "id": str(p.id),
            "name": p.name,
            "category": p.category.name,
            "category_id": p.category_id,
            "price": str(p.selling_price),
            "barcode": p.barcode or "",
            "photo": p.photo.url if p.photo else "",
        }
        for p in products
    ]

    return render(
        request,
        "inventory/pos.html",
        {
            "form": payment_form,
            "items_formset": items_formset,
            "products": products,
            "categories": categories,
            "warehouse": employee_wh,
            "stock_positions": warehouse_stock_counts,
            "keypad_rows": keypad_rows,
            "price_map": price_map,
            "stock_map": stock_map,
            "barcode_map": barcode_map,
            "products_payload": products_payload,
            "next_receipt": next_receipt,
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


def incoming_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "incoming")
    records = Incoming.objects.select_related("product", "warehouse").order_by("-date", "-id")
    return render(request, "inventory/incoming_list.html", {"records": records})


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


def incoming_delete(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "incoming")
    incoming = get_object_or_404(Incoming, pk=pk)
    employee_wh = _user_warehouse(request.user)
    if employee_wh and not request.user.is_superuser and incoming.warehouse_id != employee_wh.id:
        messages.error(request, "Нет доступа к этому приходу.")
        return redirect("inventory:incoming_list")

    if request.method == "POST":
        try:
            with transaction.atomic():
                adjust_stock(incoming.warehouse, incoming.product, -incoming.quantity)
                incoming.delete()
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
        else:
            messages.success(request, "Приход удален.")
    return redirect("inventory:incoming_list")


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


def movement_list(request):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "movements")
    records = (
        Movement.objects.select_related("product", "from_warehouse", "to_warehouse")
        .order_by("-date", "-id")
    )
    return render(request, "inventory/movement_list.html", {"records": records})


def movement_edit(request, pk):
    if not request.user.is_authenticated:
        return redirect("inventory:login")
    _require_access(request.user, "movements")
    movement = get_object_or_404(Movement, pk=pk)
    if request.method == "POST":
        form = MovementForm(request.POST, instance=movement, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
            except ValidationError as exc:
                form.add_error(None, exc.messages[0])
            else:
                messages.success(request, "Перемещение обновлено.")
                return redirect("inventory:movement_list")
    else:
        form = MovementForm(instance=movement, user=request.user)
    return render(
        request,
        "inventory/operations_movement.html",
        {"form": form, "title": "Изменить перемещение", "submit_label": "Сохранить"},
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
        Sale.objects.select_related("warehouse", "seller")
        .prefetch_related("items__product")
        .order_by("-created_at")
    )
    if employee_wh and not request.user.is_superuser:
        sales = sales.filter(warehouse=employee_wh)
    form = SalesReportFilterForm(request.GET or None, user=request.user, employee_wh=employee_wh)
    start_date = end_date = None
    if form.is_valid():
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        selected_wh = form.cleaned_data.get("warehouse")
        if selected_wh:
            sales = sales.filter(warehouse=selected_wh)
        if start_date:
            sales = sales.filter(created_at__date__gte=start_date)
        if end_date:
            sales = sales.filter(created_at__date__lte=end_date)
    profit_expression = ExpressionWrapper(
        (F("items__price") - F("items__product__purchase_price")) * F("items__quantity"),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    sales = sales.annotate(
        profit=Coalesce(Sum(profit_expression), Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))),
        total_items=Coalesce(Sum("items__quantity"), 0),
    )
    sales_count = sales.count()

    zero_decimal = Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))
    raw_stats = sales.aggregate(
        total_qty=Coalesce(Sum("items__quantity"), 0),
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
    for sale in sales_queryset.prefetch_related("items__product"):
        sale_date = sale.created_at
        if timezone.is_aware(sale_date):
            sale_date_display = timezone.localtime(sale_date).strftime("%Y-%m-%d %H:%M")
        else:
            sale_date_display = sale_date.strftime("%Y-%m-%d %H:%M")
        for item in sale.items.all():
            writer.writerow([
                sale_date_display,
                sale.warehouse.name,
                item.product.name,
                item.quantity,
                item.price,
                item.total,
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
