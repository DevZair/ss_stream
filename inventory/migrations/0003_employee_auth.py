# Generated manually: add AccessSection, employee auth fields (idempotent)
from django.db import migrations, models
from django.conf import settings
from django.db import transaction


def _table_exists(schema_editor, table_name: str) -> bool:
    return table_name in schema_editor.connection.introspection.table_names()


def _column_exists(schema_editor, table_name: str, column_name: str) -> bool:
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(col.name == column_name for col in columns)


def _get_model(apps, model_label: str):
    try:
        return apps.get_model("inventory", model_label)
    except LookupError:
        from inventory import models as runtime_models
        return getattr(runtime_models, model_label)


def _create_model_if_missing(apps, schema_editor, model_label: str) -> None:
    model = _get_model(apps, model_label)
    table = model._meta.db_table
    if _table_exists(schema_editor, table):
        return
    schema_editor.create_model(model)


def _add_field_if_missing(apps, schema_editor, model_label: str, field_name: str, field: models.Field) -> None:
    model = _get_model(apps, model_label)
    table = model._meta.db_table
    if not _table_exists(schema_editor, table) or _column_exists(schema_editor, table, field_name):
        return
    # Resolve related model if provided as a string (auth.User etc.)
    remote_model = getattr(getattr(field, "remote_field", None), "model", None)
    if isinstance(remote_model, str):
        if "." in remote_model:
            app_label, model_name = remote_model.split(".", 1)
        else:
            app_label, model_name = model._meta.app_label, remote_model
        field.remote_field.model = apps.get_model(app_label, model_name)
        if getattr(field.remote_field, "field_name", None) in (None, ""):
            field.remote_field.field_name = field.remote_field.model._meta.pk.name
    field.set_attributes_from_name(field_name)
    schema_editor.add_field(model, field)


def _ensure_m2m_if_missing(apps, schema_editor, model_label: str, field_name: str):
    model = _get_model(apps, model_label)
    field = model._meta.get_field(field_name)
    through = field.remote_field.through
    table = through._meta.db_table
    if _table_exists(schema_editor, table):
        return
    schema_editor.create_model(through)


def create_default_sections(apps, schema_editor):
    AccessSection = _get_model(apps, "AccessSection")
    defaults = [
        ("products", "Товары"),
        ("warehouses", "Склады"),
        ("operations", "Операции"),
        ("reports", "Отчеты"),
    ]
    with transaction.atomic():
        for slug, name in defaults:
            AccessSection.objects.get_or_create(slug=slug, defaults={"name": name})


def forwards(apps, schema_editor):
    _create_model_if_missing(apps, schema_editor, "AccessSection")
    _add_field_if_missing(
        apps,
        schema_editor,
        "Employee",
        "user",
        models.OneToOneField(
            blank=True,
            null=True,
            on_delete=models.deletion.CASCADE,
            related_name="employee_profile",
            to=settings.AUTH_USER_MODEL,
        ),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Employee",
        "position",
        models.CharField(
            choices=[
                ("manager", "Менеджер склада"),
                ("operator", "Оператор выдачи"),
                ("accountant", "Бухгалтер/учет"),
            ],
            default="manager",
            max_length=50,
        ),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Employee",
        "status",
        models.CharField(
            choices=[("active", "Активен"), ("blocked", "Заблокирован")],
            default="active",
            max_length=20,
        ),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Employee",
        "access_sections",
        models.ManyToManyField(
            blank=True,
            related_name="employees",
            to="inventory.accesssection",
        ),
    )
    _ensure_m2m_if_missing(apps, schema_editor, "Employee", "access_sections")
    create_default_sections(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_extend_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
            state_operations=[
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
            ],
        ),
    ]
