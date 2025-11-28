from django import forms

from .models import Employee, Incoming, Movement, Product, Sale, Warehouse


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
            if isinstance(widget, forms.CheckboxInput):
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


class WarehouseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ("name", "location")


class EmployeeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Employee
        fields = ("full_name", "position", "warehouse")


class IncomingForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Incoming
        fields = ("product", "warehouse", "quantity", "date")
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class MovementForm(StyledFormMixin, forms.ModelForm):
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
    class Meta:
        model = Sale
        fields = ("product", "warehouse", "quantity", "price", "payment_method")
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01"}),
        }
        labels = {
            "price": "Цена продажи",
            "payment_method": "Метод оплаты",
        }


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
