from django.db import migrations


SECTIONS = [
    ("categories", "Категории"),
    ("products", "Товары"),
    ("warehouses", "Склады"),
    ("employees", "Сотрудники"),
    ("stocks", "Остатки"),
    ("operations", "Операции"),
    ("reports", "Отчеты"),
    ("incoming", "Поступления"),
    ("movements", "Перемещения"),
    ("sales", "Продажи"),
]

POSITION_MAP = {
    "manager": "admin",
    "operator": "storekeeper",
    "accountant": "accountant",
}


def ensure_sections(apps, schema_editor):
    AccessSection = apps.get_model("inventory", "AccessSection")
    for slug, name in SECTIONS:
        AccessSection.objects.get_or_create(slug=slug, defaults={"name": name})


def normalize_positions(apps, schema_editor):
    Employee = apps.get_model("inventory", "Employee")
    for old, new in POSITION_MAP.items():
        Employee.objects.filter(position=old).update(position=new)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0003_employee_auth"),
    ]

    operations = [
        migrations.RunPython(ensure_sections, migrations.RunPython.noop),
        migrations.RunPython(normalize_positions, migrations.RunPython.noop),
    ]
