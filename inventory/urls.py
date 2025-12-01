from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "inventory"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="inventory/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.product_list, name="product_list"),
    path("products/add/", views.product_create, name="product_add"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_add"),
    path("employees/", views.employee_list, name="employee_list"),
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/add/", views.warehouse_create, name="warehouse_add"),
    path("employees/add/", views.employee_create, name="employee_add"),
    path("employees/<int:pk>/edit/", views.employee_update, name="employee_edit"),
    path("incoming/add/", views.incoming_create, name="incoming_add"),
    path("movements/add/", views.movement_create, name="movement_add"),
    path("sales/add/", views.sale_create, name="sale_add"),
    path("stocks/", views.stock_list, name="stock_list"),
    path("reports/sales/", views.sales_report, name="sales_report"),
]
