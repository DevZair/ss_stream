# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    first_name = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class DjangoAdminLog(models.Model):
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.PositiveSmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    action_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class InventoryAccesssection(models.Model):
    slug = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'inventory_accesssection'


class InventoryActivitylog(models.Model):
    action = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField(blank=True, null=True)
    details = models.TextField()
    created_at = models.DateTimeField()
    employee = models.ForeignKey('InventoryEmployee', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventory_activitylog'


class InventoryCategory(models.Model):
    name = models.CharField(unique=True, max_length=150)
    created_at = models.DateTimeField()
    description = models.TextField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'inventory_category'


class InventoryEmployee(models.Model):
    full_name = models.CharField(max_length=255)
    warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING)
    user = models.OneToOneField(AuthUser, models.DO_NOTHING, blank=True, null=True)
    status = models.CharField(max_length=20)
    position = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'inventory_employee'


class InventoryEmployeeAccessSections(models.Model):
    employee = models.ForeignKey(InventoryEmployee, models.DO_NOTHING)
    accesssection = models.ForeignKey(InventoryAccesssection, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'inventory_employee_access_sections'
        unique_together = (('employee', 'accesssection'),)


class InventoryIncoming(models.Model):
    quantity = models.PositiveIntegerField()
    product = models.ForeignKey('InventoryProduct', models.DO_NOTHING)
    warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING)
    date = models.DateField()

    class Meta:
        managed = False
        db_table = 'inventory_incoming'


class InventoryMovement(models.Model):
    quantity = models.PositiveIntegerField()
    from_warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING)
    product = models.ForeignKey('InventoryProduct', models.DO_NOTHING)
    to_warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING, related_name='inventorymovement_to_warehouse_set')
    date = models.DateField()

    class Meta:
        managed = False
        db_table = 'inventory_movement'


class InventoryProduct(models.Model):
    name = models.CharField(max_length=255)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    selling_price = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    photo = models.CharField(max_length=100, blank=True, null=True)
    category = models.ForeignKey(InventoryCategory, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'inventory_product'
        unique_together = (('name', 'category'),)


class InventorySale(models.Model):
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    total = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    payment_method = models.CharField(max_length=10)
    created_at = models.DateTimeField()
    product = models.ForeignKey(InventoryProduct, models.DO_NOTHING)
    warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING)
    payment_details = models.CharField(max_length=255)
    cash_amount = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    halyk_amount = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    kaspi_amount = models.DecimalField(max_digits=10, decimal_places=5)  # max_digits and decimal_places have been guessed, as this database handles decimal fields as float
    seller = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'inventory_sale'


class InventorySalesreport(models.Model):
    created_at = models.DateTimeField()
    sale = models.ForeignKey(InventorySale, models.DO_NOTHING)
    notes = models.TextField()
    report_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'inventory_salesreport'


class InventoryStock(models.Model):
    quantity = models.PositiveIntegerField()
    product = models.ForeignKey(InventoryProduct, models.DO_NOTHING)
    warehouse = models.ForeignKey('InventoryWarehouse', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'inventory_stock'
        unique_together = (('warehouse', 'product'),)


class InventoryWarehouse(models.Model):
    name = models.CharField(unique=True, max_length=150)
    location = models.CharField(max_length=255)
    code = models.CharField(unique=True, max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'inventory_warehouse'


class InventoryWarehouseprofile(models.Model):
    manager_name = models.CharField(max_length=255)
    contact_phone = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField()
    temperature_controlled = models.BooleanField()
    warehouse = models.OneToOneField(InventoryWarehouse, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'inventory_warehouseprofile'
