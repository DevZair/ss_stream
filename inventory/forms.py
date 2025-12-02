from django import forms
from django.contrib.auth import get_user_model

from .models import (
    AccessSection,
    Category,
    Employee,
    Incoming,
    Movement,
    Product,
    Sale,
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
            "category",
            "purchase_price",
            "selling_price",
            "photo",
        )
        widgets = {
            "purchase_price": forms.NumberInput(attrs={"step": "0.01"}),
            "selling_price": forms.NumberInput(attrs={"step": "0.01"}),
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


class SaleForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user and hasattr(user, "employee_profile") and not user.is_superuser:
            wh = user.employee_profile.warehouse
            self.fields["warehouse"].queryset = Warehouse.objects.filter(pk=wh.pk)
            self.fields["warehouse"].initial = wh
        self.fields["price"].widget.attrs.setdefault("placeholder", "Цена продажи")
        for amount_field in ("cash_amount", "halyk_amount", "kaspi_amount"):
            if amount_field in self.fields:
                self.fields[amount_field].widget.attrs.setdefault("step", "0.01")
                self.fields[amount_field].widget.attrs.setdefault("placeholder", "0")
        # Прячем поля разбиения, если выбран не смешанный метод (JS откроет при смешанной)
        self.fields["cash_amount"].widget.attrs.setdefault("class", "form-control split-field")
        self.fields["halyk_amount"].widget.attrs.setdefault("class", "form-control split-field")
        self.fields["kaspi_amount"].widget.attrs.setdefault("class", "form-control split-field")

    class Meta:
        model = Sale
        fields = (
            "product",
            "warehouse",
            "quantity",
            "price",
            "payment_method",
            "cash_amount",
            "halyk_amount",
            "kaspi_amount",
            "payment_details",
        )
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "price": "Цена продажи",
            "payment_method": "Метод оплаты",
            "cash_amount": "Наличные",
            "halyk_amount": "Halyk/Карта",
            "kaspi_amount": "Kaspi",
            "payment_details": "Комментарий по оплате",
        }

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get("product")
        quantity = cleaned.get("quantity") or 0
        price = cleaned.get("price") or (product.selling_price if product else None)
        if price is None:
            return cleaned
        total = (price or 0) * quantity
        cleaned["price"] = price
        payment_method = cleaned.get("payment_method")
        cash = cleaned.get("cash_amount") or 0
        halyk = cleaned.get("halyk_amount") or 0
        kaspi = cleaned.get("kaspi_amount") or 0

        if payment_method != "mixed":
            cash = halyk = kaspi = 0
            if payment_method == "cash":
                cash = total
            elif payment_method == "halyk":
                halyk = total
            elif payment_method == "kaspi":
                kaspi = total
        else:
            paid_sum = cash + halyk + kaspi
            if paid_sum <= 0:
                cash = total
                halyk = 0
                kaspi = 0
            elif paid_sum != total:
                # нормализуем: добавляем разницу в наличные
                cash = cash + (total - paid_sum)

        cleaned["cash_amount"] = cash
        cleaned["halyk_amount"] = halyk
        cleaned["kaspi_amount"] = kaspi
        return cleaned


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
