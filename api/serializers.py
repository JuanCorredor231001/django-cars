from datetime import date

from django.db import transaction
from rest_framework import serializers

from auditoria.models import AuditoriaLog
from comercial.models import Cliente, Empleado, Venta
from inventario.models import Mantenimiento, Marca, Modelo, Vehiculo


class MarcaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marca
        fields = "__all__"


class ModeloSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)

    class Meta:
        model = Modelo
        fields = ["id", "nombre", "tipo", "marca", "marca_nombre"]


class VehiculoSerializer(serializers.ModelSerializer):
    modelo_nombre = serializers.CharField(source="modelo.__str__", read_only=True)

    class Meta:
        model = Vehiculo
        fields = [
            "id", "vin", "modelo", "modelo_nombre", "anio", "color",
            "kilometraje", "precio", "estado", "fecha_ingreso",
        ]

    def to_internal_value(self, data):
        # Normaliza el VIN antes de que corran los validadores de formato.
        if isinstance(data.get("vin"), str):
            data = {**data, "vin": data["vin"].strip().upper()}
        return super().to_internal_value(data)

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor que 0.")
        return value

    def validate_estado(self, value):
        # 'vendido' solo se alcanza (y solo se revierte) a traves de Venta, nunca editando el vehiculo.
        vendido = Vehiculo.Estado.VENDIDO
        actual = self.instance.estado if self.instance else None
        if value == vendido and actual != vendido:
            raise serializers.ValidationError("Un vehículo solo pasa a 'vendido' registrando una venta.")
        if actual == vendido and value != vendido:
            raise serializers.ValidationError("Un vehículo vendido no cambia de estado; elimine la venta (gerente).")
        return value

    def validate_anio(self, value):
        if value < 1950 or value > date.today().year + 1:
            raise serializers.ValidationError("Año fuera de rango.")
        return value


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"


class EmpleadoSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Empleado
        fields = ["id", "user", "username", "cargo", "comision_pct"]


class VentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = ["id", "vehiculo", "cliente", "empleado", "fecha", "precio_final", "metodo_pago"]
        # el empleado lo fija el servidor segun quien autentica (M2); el gerente puede indicarlo
        extra_kwargs = {"empleado": {"required": False}}

    def validate_precio_final(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio final debe ser mayor que 0.")
        return value

    def validate_vehiculo(self, vehiculo):
        if self.instance is not None and vehiculo != self.instance.vehiculo:
            raise serializers.ValidationError("No se puede cambiar el vehículo de una venta; anúlela y cree otra.")
        if self.instance is None and vehiculo.estado == Vehiculo.Estado.VENDIDO:
            raise serializers.ValidationError("El vehículo ya fue vendido.")
        return vehiculo

    @transaction.atomic
    def create(self, validated_data):
        # Bloqueo de fila: evita vender dos veces el mismo vehiculo en concurrencia.
        vehiculo = Vehiculo.objects.select_for_update().get(pk=validated_data["vehiculo"].pk)
        if vehiculo.estado == Vehiculo.Estado.VENDIDO:
            raise serializers.ValidationError({"vehiculo": "El vehículo ya fue vendido."})
        venta = super().create(validated_data)
        vehiculo.estado = Vehiculo.Estado.VENDIDO
        vehiculo.save(update_fields=["estado"])
        return venta


class MantenimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mantenimiento
        fields = "__all__"

    def validate_costo(self, value):
        if value < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return value


class AuditoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditoriaLog
        fields = "__all__"
