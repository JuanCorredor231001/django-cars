"""Carga datos de demostracion. Contrasena de los usuarios demo: variable DEMO_PASSWORD de .env."""
import os
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comercial.models import Cliente, Empleado, Venta
from inventario.models import Mantenimiento, Marca, Modelo, Vehiculo

MARCAS = {
    "Toyota": ("Japón", [("Corolla", "sedan"), ("Hilux", "pickup"), ("RAV4", "suv")]),
    "Mazda": ("Japón", [("Mazda 3", "sedan"), ("CX-5", "suv")]),
    "Renault": ("Francia", [("Sandero", "hatchback"), ("Duster", "suv")]),
    "Chevrolet": ("EE. UU.", [("Onix", "hatchback"), ("Tracker", "suv")]),
}
COLORES = ["Blanco", "Negro", "Gris", "Rojo", "Azul"]
VIN_BASE = "1HGCM82633A"  # 11 caracteres; se completa con 6 digitos


class Command(BaseCommand):
    help = "Crea marcas, modelos, vehiculos, clientes y 3 empleados demo (gerente/vendedor/tecnico)."

    @transaction.atomic
    def handle(self, *args, **opts):
        pwd = os.environ.get("DEMO_PASSWORD")
        if not pwd:
            raise CommandError("Define DEMO_PASSWORD en .env")
        User = get_user_model()
        for username, cargo, staff in (("gerente", "gerente", True), ("vendedor", "vendedor", False), ("tecnico", "tecnico", False)):
            u, creado = User.objects.get_or_create(username=username, defaults={"is_staff": staff, "is_superuser": cargo == "gerente"})
            if creado:
                u.set_password(pwd)
                u.save()
            Empleado.objects.get_or_create(user=u, defaults={"cargo": cargo, "comision_pct": 2 if cargo == "vendedor" else 0})

        n = 0
        for nombre, (pais, modelos) in MARCAS.items():
            marca, _ = Marca.objects.get_or_create(nombre=nombre, defaults={"pais_origen": pais})
            for mnombre, tipo in modelos:
                modelo, _ = Modelo.objects.get_or_create(marca=marca, nombre=mnombre, defaults={"tipo": tipo})
                for i in range(2):
                    n += 1
                    Vehiculo.objects.get_or_create(
                        vin=f"{VIN_BASE}{n:06d}",
                        defaults=dict(modelo=modelo, anio=2020 + (n % 6), color=COLORES[n % 5], kilometraje=n * 3500,
                                      precio=45_000_000 + n * 2_500_000, fecha_ingreso=date.today() - timedelta(days=n * 5)),
                    )
        for i, (nom, ape) in enumerate([("Ana", "Pérez"), ("Luis", "Gómez"), ("María", "Rojas")], start=1):
            Cliente.objects.get_or_create(documento=f"1000{i}000{i}", defaults=dict(nombres=nom, apellidos=ape, email=f"{nom.lower()}@example.com"))
        self._ventas_y_mantenimientos()
        self.stdout.write(self.style.SUCCESS("Datos demo cargados."))

    def _ventas_y_mantenimientos(self):
        """Ventas (vehiculos marcados vendidos) y mantenimientos para que haya historial que consultar."""
        vendedor = Empleado.objects.get(cargo="vendedor")
        tecnico = Empleado.objects.get(cargo="tecnico")
        clientes = list(Cliente.objects.order_by("id"))
        pagos = ["contado", "credito", "leasing"]
        for i, v in enumerate(Vehiculo.objects.order_by("id")[:6]):
            if Venta.objects.filter(vehiculo=v).exists():
                continue
            Venta.objects.create(vehiculo=v, cliente=clientes[i % len(clientes)], empleado=vendedor,
                                 fecha=date.today() - timedelta(days=30 * (i % 4) + 3),
                                 precio_final=v.precio * 95 // 100, metodo_pago=pagos[i % 3])
            Vehiculo.objects.filter(pk=v.pk).update(estado=Vehiculo.Estado.VENDIDO)
        for i, v in enumerate(Vehiculo.objects.order_by("id")[:8]):
            for k in range(1 + i % 3):
                Mantenimiento.objects.get_or_create(
                    vehiculo=v, descripcion=f"Revisión {k + 1}",
                    defaults=dict(tecnico=tecnico, fecha=date.today() - timedelta(days=15 * (k + 1)), costo=150_000 + 50_000 * k + 10_000 * i))
