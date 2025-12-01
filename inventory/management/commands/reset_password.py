import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Сброс пароля пользователя. Пример: python manage.py reset_password admin --password newpass"

    def add_arguments(self, parser):
        parser.add_argument("username", help="Логин пользователя")
        parser.add_argument(
            "--password",
            dest="password",
            help="Новый пароль. Если не указан, будет запрошен интерактивно.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options.get("password")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"Пользователь '{username}' не найден") from exc

        if not password:
            password = getpass.getpass(prompt="Новый пароль: ")
            confirm = getpass.getpass(prompt="Повторите пароль: ")
            if password != confirm:
                raise CommandError("Пароли не совпадают")

        if not password:
            raise CommandError("Пароль не может быть пустым")

        user.set_password(password)
        user.is_active = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f"Пароль для '{username}' обновлен."))
