from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("products/add/", views.product_create, name="product_add"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/add/", views.warehouse_create, name="warehouse_add"),
    path("employees/add/", views.employee_create, name="employee_add"),
    path("incoming/add/", views.incoming_create, name="incoming_add"),
    path("movements/add/", views.movement_create, name="movement_add"),
    path("sales/add/", views.sale_create, name="sale_add"),
    path("stocks/", views.stock_list, name="stock_list"),
    path("reports/sales/", views.sales_report, name="sales_report"),
]
