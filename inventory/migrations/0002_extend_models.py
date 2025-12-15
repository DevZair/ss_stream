# Generated manually to align with updated models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.db import transaction
import inventory.models


def _table_exists(schema_editor, table_name: str) -> bool:
    return table_name in schema_editor.connection.introspection.table_names()


def _column_exists(schema_editor, table_name: str, column_name: str) -> bool:
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(cursor, table_name)
    return any(col.name == column_name for col in columns)


def _add_field_if_missing(apps, schema_editor, model_label: str, field_name: str, field: models.Field) -> None:
    model = _get_model(apps, model_label)
    table = model._meta.db_table
    if not _table_exists(schema_editor, table) or _column_exists(schema_editor, table, field_name):
        return
    field.set_attributes_from_name(field_name)
    schema_editor.add_field(model, field)


def _create_model_if_missing(apps, schema_editor, model_label: str) -> None:
    model = _get_model(apps, model_label)
    table = model._meta.db_table
    if _table_exists(schema_editor, table):
        return
    schema_editor.create_model(model)


def _ensure_index(apps, schema_editor, model_label: str, fields: list[str], name: str) -> None:
    model = _get_model(apps, model_label)
    table = model._meta.db_table
    if not _table_exists(schema_editor, table):
        return
    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(cursor, table)
    for info in constraints.values():
        if info.get("index") and info.get("columns") == fields:
            return
    schema_editor.add_index(model, models.Index(fields=fields, name=name))


def _ensure_warehouse_code(apps, schema_editor):
    model = _get_model(apps, "Warehouse")
    table = model._meta.db_table
    if not _table_exists(schema_editor, table) or _column_exists(schema_editor, table, "code"):
        return

    # Step 1: add nullable column without uniqueness to avoid conflicts during backfill.
    temp_field = models.CharField(max_length=20, null=True, default=None)
    temp_field.set_attributes_from_name("code")
    schema_editor.add_field(model, temp_field)

    # Step 2: backfill unique codes for existing rows using raw SQL (model state doesn't know the field yet).
    with transaction.atomic(), schema_editor.connection.cursor() as cursor:
        cursor.execute(f"SELECT id FROM {table}")
        pks = [row[0] for row in cursor.fetchall()]
        existing_codes = set()
        updates = []
        for pk in pks:
            code = inventory.models.generate_warehouse_code()
            while code in existing_codes:
                code = inventory.models.generate_warehouse_code()
            existing_codes.add(code)
            updates.append((code, pk))
        for code, pk in updates:
            cursor.execute(f"UPDATE {table} SET code=%s WHERE id=%s", (code, pk))

    # Step 3: alter column to the final NOT NULL + UNIQUE definition.
    final_field = models.CharField(
        max_length=20,
        unique=True,
        default=inventory.models.generate_warehouse_code,
        editable=False,
    )
    final_field.set_attributes_from_name("code")
    schema_editor.alter_field(model, temp_field, final_field)


def _get_model(apps, model_label: str):
    """
    Fetch model from historical state; if absent (e.g. new model in this migration), fallback to current app model.
    """
    try:
        return apps.get_model("inventory", model_label)
    except LookupError:
        from inventory import models as runtime_models
        return getattr(runtime_models, model_label)


def forwards(apps, schema_editor):
    _add_field_if_missing(
        apps,
        schema_editor,
        "Category",
        "created_at",
        models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Category",
        "description",
        models.TextField(blank=True),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Category",
        "is_active",
        models.BooleanField(default=True),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "Warehouse",
        "created_at",
        models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
    )
    _ensure_warehouse_code(apps, schema_editor)
    _create_model_if_missing(apps, schema_editor, "WarehouseProfile")
    _add_field_if_missing(
        apps,
        schema_editor,
        "SalesReport",
        "notes",
        models.TextField(blank=True),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "SalesReport",
        "report_type",
        models.CharField(
            choices=[("sale", "По продажам"), ("monthly", "Итоговый отчет")],
            default="sale",
            max_length=20,
        ),
    )
    _add_field_if_missing(
        apps,
        schema_editor,
        "SalesReport",
        "status",
        models.CharField(
            choices=[("draft", "Черновик"), ("final", "Готов")],
            default="final",
            max_length=20,
        ),
    )
    _ensure_index(apps, schema_editor, "Incoming", ["date"], "inventory_incoming_date_idx")
    _ensure_index(apps, schema_editor, "Movement", ["date"], "inventory_movement_date_idx")
    _ensure_index(apps, schema_editor, "Sale", ["created_at"], "inventory_sale_created_at_idx")


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(forwards, migrations.RunPython.noop),
            ],
            state_operations=[
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
            ],
        ),
    ]
