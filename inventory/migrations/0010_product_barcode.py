import secrets
from django.db import migrations, models
from django.db.models import Q


def generate_barcode(length: int = 13) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def assign_barcodes(apps, schema_editor):
    Product = apps.get_model("inventory", "Product")
    existing = set(
        Product.objects.exclude(barcode__isnull=True)
        .exclude(barcode="")
        .values_list("barcode", flat=True)
    )
    to_update = Product.objects.filter(Q(barcode__isnull=True) | Q(barcode=""))
    for product in to_update.iterator():
        for _ in range(10):
            candidate = generate_barcode()
            if candidate in existing:
                continue
            if Product.objects.filter(barcode=candidate).exists():
                continue
            product.barcode = candidate
            product.save(update_fields=["barcode"])
            existing.add(candidate)
            break
        else:
            raise ValueError("Не удалось сгенерировать уникальный штрихкод для товара.")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0009_alter_employee_position"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="barcode",
            field=models.CharField(
                blank=True,
                help_text="Оставьте пустым — сгенерируем уникальный штрихкод",
                max_length=32,
                null=True,
                unique=True,
            ),
        ),
        migrations.RunPython(assign_barcodes, migrations.RunPython.noop),
    ]
