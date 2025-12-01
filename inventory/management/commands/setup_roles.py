from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


def _codename(model: str, action: str) -> str:
    return f"{action}_{model}"


def _perms_for(models: list[str], actions: list[str]) -> list[str]:
    codenames: list[str] = []
    for model in models:
        for action in actions:
            codenames.append(_codename(model, action))
    return codenames


class Command(BaseCommand):
    help = "Создает группы с правами: Администратор, Менеджер склада, Оператор"

    def handle(self, *args, **options):
        inventory_models = [
            "category",
            "product",
            "warehouse",
            "warehouseprofile",
            "employee",
            "incoming",
            "movement",
            "sale",
            "salesreport",
            "stock",
        ]

        groups_config = {
            "Администратор": _perms_for(inventory_models, ["add", "change", "delete", "view"]),
            "Менеджер склада": _perms_for(
                ["product", "warehouse", "warehouseprofile", "employee", "incoming", "movement", "sale", "salesreport", "stock"],
                ["add", "change", "view"],
            ),
            "Оператор": _perms_for(
                ["incoming", "movement", "sale", "stock"],
                ["add", "view"],
            )
            + _perms_for(["product", "warehouse"], ["view"]),
        }

        for group_name, codenames in groups_config.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            perms = list(Permission.objects.filter(codename__in=codenames))
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"Группа '{group_name}' обновлена ({len(perms)} прав)."))

        self.stdout.write(self.style.SUCCESS("Роли настроены. Назначьте их пользователям через админку."))
