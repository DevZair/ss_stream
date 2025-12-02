from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = "Складской учет"

    def ready(self):
        # ensure template tags are discoverable
        import inventory.templatetags.inventory_extras  # noqa: F401
