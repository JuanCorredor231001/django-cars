from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


def anio_maximo():
    return date.today().year + 1


class Marca(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    pais_origen = models.CharField(max_length=60, blank=True)

    class Meta:
        db_table = "marca"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Modelo(models.Model):
    class Tipo(models.TextChoices):
        SEDAN = "sedan", "Sedán"
        SUV = "suv", "SUV"
        PICKUP = "pickup", "Pickup"
        HATCHBACK = "hatchback", "Hatchback"
        COUPE = "coupe", "Coupé"
        OTRO = "otro", "Otro"

    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.SEDAN)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="modelos")

    class Meta:
        db_table = "modelo"
        ordering = ["marca__nombre", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["marca", "nombre"], name="uq_modelo_marca_nombre")
        ]

    def __str__(self):
        return f"{self.marca} {self.nombre}"


class Vehiculo(models.Model):
    class Estado(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        RESERVADO = "reservado", "Reservado"
        VENDIDO = "vendido", "Vendido"

    vin = models.CharField(
        max_length=17,
        unique=True,
        validators=[RegexValidator(r"^[A-HJ-NPR-Z0-9]{17}$", "VIN de 17 caracteres (sin I, O, Q).")],
    )
    modelo = models.ForeignKey(Modelo, on_delete=models.PROTECT, related_name="vehiculos")
    anio = models.PositiveSmallIntegerField(validators=[MinValueValidator(1950)])
    color = models.CharField(max_length=40)
    kilometraje = models.PositiveIntegerField(default=0)
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.DISPONIBLE)
    fecha_ingreso = models.DateField(default=date.today)

    class Meta:
        db_table = "vehiculo"
        ordering = ["-fecha_ingreso"]
        indexes = [models.Index(fields=["estado"]), models.Index(fields=["fecha_ingreso"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gt=0), name="ck_vehiculo_precio_pos"),
            models.CheckConstraint(
                condition=models.Q(anio__gte=1950, anio__lte=2100), name="ck_vehiculo_anio_rango"
            ),
        ]

    def clean(self):
        if self.anio and self.anio > anio_maximo():
            raise ValidationError({"anio": f"El año no puede superar {anio_maximo()}."})

    def __str__(self):
        return f"{self.modelo} {self.anio} ({self.vin})"


class Mantenimiento(models.Model):
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, related_name="mantenimientos")
    tecnico = models.ForeignKey(
        "comercial.Empleado", on_delete=models.PROTECT, related_name="mantenimientos"
    )
    fecha = models.DateField(default=date.today)
    descripcion = models.TextField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "mantenimiento"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(condition=models.Q(costo__gte=0), name="ck_mant_costo_nonneg")
        ]

    def __str__(self):
        return f"Mantenimiento {self.vehiculo_id} {self.fecha}"
