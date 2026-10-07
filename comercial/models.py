from datetime import date

from django.conf import settings
from django.db import models


class Cliente(models.Model):
    documento = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=160, blank=True)

    class Meta:
        db_table = "cliente"
        ordering = ["apellidos", "nombres"]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class Empleado(models.Model):
    class Cargo(models.TextChoices):
        VENDEDOR = "vendedor", "Vendedor"
        GERENTE = "gerente", "Gerente"
        TECNICO = "tecnico", "Técnico"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="empleado"
    )
    cargo = models.CharField(max_length=12, choices=Cargo.choices, default=Cargo.VENDEDOR)
    comision_pct = models.DecimalField(max_digits=4, decimal_places=2, default=0)

    class Meta:
        db_table = "empleado"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(comision_pct__gte=0, comision_pct__lte=100),
                name="ck_empleado_comision_rango",
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.cargo})"


class Venta(models.Model):
    class MetodoPago(models.TextChoices):
        CONTADO = "contado", "Contado"
        CREDITO = "credito", "Crédito"
        LEASING = "leasing", "Leasing"

    vehiculo = models.OneToOneField(
        "inventario.Vehiculo", on_delete=models.PROTECT, related_name="venta"
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="compras")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="ventas")
    fecha = models.DateField(default=date.today)
    precio_final = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(max_length=10, choices=MetodoPago.choices)

    class Meta:
        db_table = "venta"
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["fecha"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(precio_final__gt=0), name="ck_venta_precio_pos")
        ]

    def __str__(self):
        return f"Venta {self.pk} - {self.vehiculo_id}"
