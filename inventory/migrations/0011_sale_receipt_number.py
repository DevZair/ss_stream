from django.db import migrations, models


def fill_receipt_numbers(apps, schema_editor):
    Sale = apps.get_model("inventory", "Sale")
    number = 1
    # Заполним чекам последовательные номера по дате создания
    for sale in Sale.objects.order_by("created_at", "id").iterator():
        sale.receipt_number = number
        sale.save(update_fields=["receipt_number"])
        number += 1


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0010_product_barcode"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="receipt_number",
            field=models.PositiveIntegerField(db_index=True, null=True, unique=False),
        ),
        migrations.RunPython(fill_receipt_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="sale",
            name="receipt_number",
            field=models.PositiveIntegerField(db_index=True, default=0, unique=True),
        ),
    ]
