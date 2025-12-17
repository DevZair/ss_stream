from decimal import Decimal
from django.db import migrations, models


def backfill_sale_items(apps, schema_editor):
    Sale = apps.get_model("inventory", "Sale")
    SaleItem = apps.get_model("inventory", "SaleItem")
    for sale in Sale.objects.all().iterator():
        if sale.product_id is None:
            continue
        if SaleItem.objects.filter(sale=sale).exists():
            continue
        SaleItem.objects.create(
            sale=sale,
            product_id=sale.product_id,
            quantity=sale.quantity or 0,
            price=sale.price or Decimal("0.00"),
            total=sale.total or Decimal("0.00"),
        )
        # ensure total is consistent
        expected_total = (sale.price or Decimal("0.00")) * Decimal(sale.quantity or 0)
        if sale.total != expected_total:
            sale.total = expected_total
            sale.save(update_fields=["total"])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0010_product_barcode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sale",
            name="product",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="sales", to="inventory.product"),
        ),
        migrations.AlterField(
            model_name="sale",
            name="quantity",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="SaleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.PositiveIntegerField()),
                ("price", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("product", models.ForeignKey(on_delete=models.deletion.PROTECT, related_name="sale_items", to="inventory.product")),
                ("sale", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="items", to="inventory.sale")),
            ],
            options={
                "verbose_name": "Позиция продажи",
                "verbose_name_plural": "Позиции продаж",
            },
        ),
        migrations.RunPython(backfill_sale_items, migrations.RunPython.noop),
    ]
