"""Crea un usuario con su ficha de empleado (necesaria para entrar a la API y al panel).

    python manage.py crear_empleado --username maria --cargo vendedor

La contraseña se pide por consola (no queda en el historial) y se valida con los
validadores de contraseña del proyecto. Cargos: gerente | vendedor | tecnico.
"""
import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comercial.models import Empleado


class Command(BaseCommand):
    help = "Crea un usuario + empleado (gerente, vendedor o tecnico)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--cargo", required=True, choices=[c.value for c in Empleado.Cargo])
        parser.add_argument("--nombres", default="")
        parser.add_argument("--apellidos", default="")
        parser.add_argument("--email", default="")

    @transaction.atomic
    def handle(self, *args, **o):
        User = get_user_model()
        if User.objects.filter(username=o["username"]).exists():
            raise CommandError(f"El usuario '{o['username']}' ya existe.")
        pwd = getpass.getpass("Contraseña: ")
        if pwd != getpass.getpass("Repetir contraseña: "):
            raise CommandError("Las contraseñas no coinciden.")
        user = User(username=o["username"], first_name=o["nombres"], last_name=o["apellidos"], email=o["email"])
        try:
            validate_password(pwd, user)
        except ValidationError as exc:
            raise CommandError("Contraseña no válida: " + " ".join(exc.messages))
        user.set_password(pwd)
        user.is_staff = o["cargo"] == "gerente"
        user.save()
        Empleado.objects.create(user=user, cargo=o["cargo"])
        self.stdout.write(self.style.SUCCESS(f"Usuario '{user.username}' creado como {o['cargo']}."))
