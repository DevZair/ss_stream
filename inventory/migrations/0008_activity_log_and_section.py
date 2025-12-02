from django.db import migrations, models
from django.conf import settings


def add_logs_section(apps, schema_editor):
    AccessSection = apps.get_model("inventory", "AccessSection")
    AccessSection.objects.get_or_create(slug="logs", defaults={"name": "Логи"})


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0007_sale_seller_and_orders_section"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActivityLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=255)),
                ("entity_type", models.CharField(blank=True, max_length=50)),
                ("entity_id", models.PositiveIntegerField(blank=True, null=True)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "employee",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="activity_logs", to="inventory.employee"),
                ),
                (
                    "user",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="activity_logs", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "verbose_name": "Активность сотрудника",
                "verbose_name_plural": "Активности сотрудников",
                "ordering": ("-created_at",),
            },
        ),
        migrations.RunPython(add_logs_section, migrations.RunPython.noop),
    ]
