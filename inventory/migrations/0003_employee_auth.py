# Generated manually: add AccessSection, employee auth fields
from django.db import migrations, models
from django.conf import settings


def create_default_sections(apps, schema_editor):
    AccessSection = apps.get_model("inventory", "AccessSection")
    defaults = [
        ("products", "Товары"),
        ("warehouses", "Склады"),
        ("operations", "Операции"),
        ("reports", "Отчеты"),
    ]
    for slug, name in defaults:
        AccessSection.objects.get_or_create(slug=slug, defaults={"name": name})


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_extend_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "verbose_name": "Раздел доступа",
                "verbose_name_plural": "Разделы доступа",
            },
        ),
        migrations.AddField(
            model_name="employee",
            name="user",
            field=models.OneToOneField(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name="employee_profile", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="employee",
            name="position",
            field=models.CharField(choices=[("manager", "Менеджер склада"), ("operator", "Оператор выдачи"), ("accountant", "Бухгалтер/учет")], default="manager", max_length=50),
        ),
        migrations.AddField(
            model_name="employee",
            name="status",
            field=models.CharField(choices=[("active", "Активен"), ("blocked", "Заблокирован")], default="active", max_length=20),
        ),
        migrations.AddField(
            model_name="employee",
            name="access_sections",
            field=models.ManyToManyField(blank=True, related_name="employees", to="inventory.accesssection"),
        ),
        migrations.RunPython(create_default_sections, migrations.RunPython.noop),
    ]
