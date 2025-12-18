from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.forms import formset_factory
from django.contrib.auth.models import Group
from django.utils import timezone

from .models import (
    AccessSection,
    Category,
    Employee,
    Incoming,
    Movement,
    Product,
    Sale,
    SaleItem,
    Warehouse,
)


EMPLOYEE_POSITIONS = [
    ("admin", "Админ"),
    ("storekeeper", "Кладовщик"),
    ("cashier", "Кассир"),
    ("accountant", "Бухгалтер"),
]

POSITION_PRESETS = {
    "admin": ["categories", "products", "warehouses", "employees", "stocks", "operations", "reports", "incoming", "movements", "sales"],
    "storekeeper": ["incoming", "movements"],
    "cashier": ["sales", "stocks"],
    "accountant": ["reports", "stocks"],
}

POSITION_GROUP_MAP = {
    "admin": "Администратор",
    "storekeeper": "Менеджер склада",
    "cashier": "Оператор",
    "accountant": "Менеджер склада",
}


def _sync_group_by_position(user, position: str):
    """
    Align user group with selected position without touching other custom groups.
    """
    target_name = POSITION_GROUP_MAP.get(position)
    if not target_name:
        return
    mapping_groups = list(Group.objects.filter(name__in=POSITION_GROUP_MAP.values()))
    if not mapping_groups:
        return  # setup_roles not executed yet
    target_group = next((g for g in mapping_groups if g.name == target_name), None)
    if not target_group:
        return
    to_remove = [g for g in mapping_groups if g.name != target_name]
    if to_remove:
        user.groups.remove(*to_remove)
    user.groups.add(target_group)


class StyledFormMixin:
    """
    Adds Bootstrap-friendly classes to widgets so templates can render fields
    without extra helpers.
    """

    widget_css_class = "form-control"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            base_class = self.widget_css_class
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                base_class = "form-check-input"
            existing_classes = widget.attrs.get("class", "").strip()
            widget.attrs["class"] = (
                f"{existing_classes} {base_class}".strip()
            )


class ProductForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "barcode",
            "category",
            "purchase_price",
            "selling_price",
            "photo",
        )
        widgets = {
            "purchase_price": forms.NumberInput(attrs={"step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01"}),
            "barcode": forms.TextInput(attrs={"placeholder": "Штрихкод (оставьте пустым для авто)"}),
        }


class CategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description", "is_active")


class WarehouseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ("name", "location")


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    position = forms.ChoiceField(choices=EMPLOYEE_POSITIONS, label="Должность")
    username = forms.CharField(label="Логин", max_length=150)
    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повторите пароль", widget=forms.PasswordInput)
    status = forms.ChoiceField(choices=Employee.STATUS_CHOICES, label="Статус")
    access_sections = forms.ModelMultipleChoiceField(
        queryset=AccessSection.objects.all(),
        required=False,
        label="Доступ к разделам",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Employee
        fields = (
            "full_name",
            "position",
            "status",
            "warehouse",
            "access_sections",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            preset_slugs = POSITION_PRESETS.get(self.initial.get("position") or Employee._meta.get_field("position").default, [])
            self.fields["access_sections"].initial = AccessSection.objects.filter(slug__in=preset_slugs)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 != p2:
            self.add_error("password2", "Пароли не совпадают")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data["username"]
        if get_user_model().objects.filter(username=username).exists():
            raise forms.ValidationError("Такой логин уже используется")
        return username

    def save(self, commit=True):
        user_model = get_user_model()
        username = self.cleaned_data["username"]
        password = self.cleaned_data["password1"]
        status = self.cleaned_data["status"]
        access_sections = self.cleaned_data.get("access_sections")
        if not access_sections:
            preset_slugs = POSITION_PRESETS.get(self.cleaned_data.get("position"), [])
            access_sections = AccessSection.objects.filter(slug__in=preset_slugs)

        user = user_model.objects.create_user(username=username, password=password)
        user.is_active = status == Employee.ACTIVE
        user.save()
        _sync_group_by_position(user, self.cleaned_data.get("position"))

        employee = super().save(commit=False)
        employee.user = user
        employee.status = status
        if commit:
            employee.save()
            self.save_m2m()
            if access_sections is not None:
                employee.access_sections.set(access_sections)
        return employee


class EmployeeUpdateForm(StyledFormMixin, forms.ModelForm):
    position = forms.ChoiceField(choices=EMPLOYEE_POSITIONS, label="Должность")
    username = forms.CharField(label="Логин", max_length=150)
    password1 = forms.CharField(label="Новый пароль", widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label="Повторите пароль", widget=forms.PasswordInput, required=False)
    status = forms.ChoiceField(choices=Employee.STATUS_CHOICES, label="Статус")
    access_sections = forms.ModelMultipleChoiceField(
        queryset=AccessSection.objects.all(),
        required=False,
        label="Доступ к разделам",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Employee
        fields = (
            "full_name",
            "position",
            "status",
            "warehouse",
            "access_sections",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields["username"].initial = self.instance.user.username
            self.fields["status"].initial = (
                Employee.ACTIVE if self.instance.user.is_active else Employee.BLOCKED
            )
        if not self.is_bound:
            preset_slugs = POSITION_PRESETS.get(self.initial.get("position") or getattr(self.instance, "position", None), [])
            if not self.instance.access_sections.exists():
                self.fields["access_sections"].initial = AccessSection.objects.filter(slug__in=preset_slugs)

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = get_user_model().objects.filter(username=username)
        if self.instance and self.instance.user:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise forms.ValidationError("Такой логин уже используется")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Пароли не совпадают")
        return cleaned

    def save(self, commit=True):
        employee = super().save(commit=False)
        user = employee.user
        if user is None:
            user = get_user_model().objects.create_user(
                username=self.cleaned_data["username"],
                password=self.cleaned_data.get("password1") or get_user_model().objects.make_random_password(),
            )
        user.username = self.cleaned_data["username"]
        user.is_active = self.cleaned_data["status"] == Employee.ACTIVE
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        user.save()
        _sync_group_by_position(user, self.cleaned_data.get("position"))

        employee.user = user
        if commit:
            employee.save()
            self.save_m2m()
            access_sections = self.cleaned_data.get("access_sections")
            if not access_sections:
                preset_slugs = POSITION_PRESETS.get(self.cleaned_data.get("position"), [])
                access_sections = AccessSection.objects.filter(slug__in=preset_slugs)
            if access_sections is not None:
                employee.access_sections.set(access_sections)
        return employee


class IncomingForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "employee_profile") and not user.is_superuser:
            wh = user.employee_profile.warehouse
            self.fields["warehouse"].queryset = Warehouse.objects.filter(pk=wh.pk)
            self.fields["warehouse"].initial = wh

    class Meta:
        model = Incoming
        fields = ("product", "warehouse", "quantity", "date")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class IncomingBatchForm(StyledFormMixin, forms.Form):
    warehouse = forms.ModelChoiceField(
        queryset=Warehouse.objects.none(),
        label="Склад",
    )
    date = forms.DateField(
        label="Дата",
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.now,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        qs = Warehouse.objects.all()
        if user and hasattr(user, "employee_profile") and not user.is_superuser:
            wh = user.employee_profile.warehouse
            qs = Warehouse.objects.filter(pk=wh.pk)
            self.fields["warehouse"].initial = wh
        self.fields["warehouse"].queryset = qs
        if not self.is_bound and not self.initial.get("date"):
            self.fields["date"].initial = timezone.now().date()


class IncomingItemForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        label="Товар",
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Количество",
        widget=forms.NumberInput(attrs={"min": 1}),
    )


IncomingItemFormSet = formset_factory(
    IncomingItemForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class MovementForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "employee_profile") and not user.is_superuser:
            wh = user.employee_profile.warehouse
            self.fields["from_warehouse"].queryset = Warehouse.objects.filter(pk=wh.pk)
            self.fields["from_warehouse"].initial = wh

    class Meta:
        model = Movement
        fields = (
            "product",
            "from_warehouse",
            "to_warehouse",
            "quantity",
            "date",
        )
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class SalePaymentForm(StyledFormMixin, forms.ModelForm):
    cash_given = forms.DecimalField(
        required=False,
        min_value=0,
        label="Наличные от клиента",
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "employee_profile") and not user.is_superuser:
            wh = user.employee_profile.warehouse
            self.fields["warehouse"].queryset = Warehouse.objects.filter(pk=wh.pk)
            self.fields["warehouse"].initial = wh
        for amount_field in ("cash_amount", "halyk_amount", "kaspi_amount", "cash_given"):
            if amount_field in self.fields:
                self.fields[amount_field].widget.attrs.setdefault("step", "0.01")
                self.fields[amount_field].widget.attrs.setdefault("placeholder", "0")
                self.fields[amount_field].widget.attrs.setdefault("class", "form-control split-field")
        self.fields["payment_details"].widget.attrs.setdefault("placeholder", "Комментарий по оплате")

    class Meta:
        model = Sale
        fields = (
            "warehouse",
            "payment_method",
            "cash_amount",
            "halyk_amount",
            "kaspi_amount",
            "payment_details",
        )
        widgets = {
            "payment_details": forms.TextInput(),
        }
        labels = {
            "payment_method": "Метод оплаты",
            "cash_amount": "Наличные",
            "halyk_amount": "Halyk/Карта",
            "kaspi_amount": "Kaspi",
            "payment_details": "Комментарий по оплате",
        }

    def normalize_payments(self, total: Decimal):
        """
        Normalize payment split to match total.
        """
        method = self.cleaned_data.get("payment_method")
        cash = self.cleaned_data.get("cash_amount") or Decimal("0.00")
        halyk = self.cleaned_data.get("halyk_amount") or Decimal("0.00")
        kaspi = self.cleaned_data.get("kaspi_amount") or Decimal("0.00")
        cash_given = self.cleaned_data.get("cash_given") or Decimal("0.00")
        change_due = Decimal("0.00")
        if method == "delayed":
            cash = halyk = kaspi = Decimal("0.00")
        elif method != "mixed":
            cash = halyk = kaspi = Decimal("0.00")
            if method == "cash":
                cash = total
            elif method == "halyk":
                halyk = total
            elif method == "kaspi":
                kaspi = total
        else:
            paid_sum = cash + halyk + kaspi
            if paid_sum <= 0:
                cash = total
                halyk = kaspi = Decimal("0.00")
            else:
                cash = cash + (total - paid_sum)
                if cash < 0:
                    overpay = -cash
                    cash = Decimal("0.00")
                    if halyk >= overpay:
                        halyk -= overpay
                        overpay = Decimal("0.00")
                    else:
                        overpay -= halyk
                        halyk = Decimal("0.00")
                    if overpay > 0:
                        kaspi = max(kaspi - overpay, Decimal("0.00"))
                paid_sum = cash + halyk + kaspi
                if paid_sum != total:
                    cash = cash + (total - paid_sum)
            cash = max(cash, Decimal("0.00"))
        if method in ("cash", "mixed"):
            paid_total = cash_given + halyk + kaspi
            diff = paid_total - total
            if diff > 0:
                change_due = diff
        self.cleaned_data["cash_amount"] = cash
        self.cleaned_data["halyk_amount"] = halyk
        self.cleaned_data["kaspi_amount"] = kaspi
        self.cleaned_data["cash_given"] = cash_given
        self.cleaned_data["change_due"] = change_due


class SaleItemForm(StyledFormMixin, forms.ModelForm):
    barcode = forms.CharField(
        label="Штрихкод",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Скан или ввод штрихкода"}),
    )

    class Meta:
        model = SaleItem
        fields = ("product", "quantity", "price")
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        barcode_value = (cleaned.get("barcode") or "").strip()
        if barcode_value and not cleaned.get("product"):
            try:
                cleaned["product"] = Product.objects.get(barcode=barcode_value)
            except Product.DoesNotExist:
                self.add_error("barcode", "Товар с таким штрихкодом не найден")
        product = cleaned.get("product")
        if product is None:
            self.add_error("product", "Выберите товар")
            return cleaned
        if not cleaned.get("price"):
            cleaned["price"] = product.selling_price
        return cleaned

SaleItemFormSet = formset_factory(SaleItemForm, extra=0, can_delete=True)


class SalesReportFilterForm(StyledFormMixin, forms.Form):
    start_date = forms.DateField(
        required=False,
        label="Дата от",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        required=False,
        label="Дата до",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    warehouse = forms.ModelChoiceField(
        required=False,
        queryset=Warehouse.objects.none(),
        label="Касса/склад",
        empty_label="Все кассы",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        employee_wh = kwargs.pop("employee_wh", None)
        super().__init__(*args, **kwargs)
        qs = Warehouse.objects.all()
        if user and not getattr(user, "is_superuser", False) and employee_wh:
            qs = qs.filter(pk=employee_wh.pk)
            self.fields["warehouse"].initial = employee_wh
        self.fields["warehouse"].queryset = qs
