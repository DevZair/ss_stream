# Generated manually to align with updated models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import inventory.models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="category",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="code",
            field=models.CharField(
                default=inventory.models.generate_warehouse_code,
                editable=False,
                max_length=20,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name="WarehouseProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("manager_name", models.CharField(blank=True, max_length=255)),
                ("contact_phone", models.CharField(blank=True, max_length=50)),
                ("capacity", models.PositiveIntegerField(default=0)),
                ("temperature_controlled", models.BooleanField(default=False)),
                (
                    "warehouse",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="inventory.warehouse",
                    ),
                ),
            ],
            options={
                "verbose_name": "Паспорт склада",
                "verbose_name_plural": "Паспорта складов",
            },
        ),
        migrations.AlterField(
            model_name="incoming",
            name="date",
            field=models.DateField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="movement",
            name="date",
            field=models.DateField(db_index=True, default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="salesreport",
            name="notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="salesreport",
            name="report_type",
            field=models.CharField(choices=[("sale", "По продажам"), ("monthly", "Итоговый отчет")], default="sale", max_length=20),
        ),
        migrations.AddField(
            model_name="salesreport",
            name="status",
            field=models.CharField(choices=[("draft", "Черновик"), ("final", "Готов")], default="final", max_length=20),
        ),
        migrations.AlterField(
            model_name="sale",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
