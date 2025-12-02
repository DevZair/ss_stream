from django.conf import settings
from django.db import migrations, models


def add_orders_section(apps, schema_editor):
    AccessSection = apps.get_model("inventory", "AccessSection")
    AccessSection.objects.get_or_create(slug="orders", defaults={"name": "Заказы"})


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0006_sale_split_amounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="seller",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="sales_made", to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(add_orders_section, migrations.RunPython.noop),
    ]
