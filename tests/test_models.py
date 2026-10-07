import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DataError, IntegrityError, transaction
from django.db.models import ProtectedError
from rest_framework.test import APIClient

from comercial.models import Cliente, Empleado, Venta
from inventario.models import Mantenimiento, Marca, Modelo, Vehiculo

pytestmark = pytest.mark.django_db


@pytest.fixture
def base():
    marca = Marca.objects.create(nombre="Mazda", pais_origen="Japón")
    modelo = Modelo.objects.create(nombre="CX-5", tipo="suv", marca=marca)
    veh = Vehiculo.objects.create(vin="JM3KFBCM0L0000001", modelo=modelo, anio=2022, color="Rojo", precio=70_000_000)
    u = get_user_model().objects.create_user("emp", password="Clave-De-Prueba-123!")
    emp = Empleado.objects.create(user=u, cargo="vendedor")
    cli = Cliente.objects.create(documento="999", nombres="Luis", apellidos="Gómez")
    return dict(marca=marca, modelo=modelo, veh=veh, emp=emp, cli=cli)


def test_marca_nombre_unico(base):
    with pytest.raises(IntegrityError), transaction.atomic():
        Marca.objects.create(nombre="Mazda")


def test_modelo_unico_por_marca(base):
    with pytest.raises(IntegrityError), transaction.atomic():
        Modelo.objects.create(nombre="CX-5", marca=base["marca"])


def test_vin_unico(base):
    with pytest.raises(IntegrityError), transaction.atomic():
        Vehiculo.objects.create(vin=base["veh"].vin, modelo=base["modelo"], anio=2020, color="Azul", precio=1)


@pytest.mark.parametrize("campo,valor", [("precio", 0), ("precio", -1), ("anio", 1900)])
def test_check_constraints_vehiculo(base, campo, valor):
    kwargs = dict(vin="JM3KFBCM0L0000002", modelo=base["modelo"], anio=2020, color="Azul", precio=10)
    kwargs[campo] = valor
    with pytest.raises(IntegrityError), transaction.atomic():
        Vehiculo.objects.create(**kwargs)


def test_vin_formato_invalido_en_full_clean(base):
    v = Vehiculo(vin="OOOOOOOOOOOOOOOOO", modelo=base["modelo"], anio=2020, color="Azul", precio=10)
    with pytest.raises(ValidationError):
        v.full_clean()


def test_anio_futuro_lejano_invalido(base):
    v = Vehiculo(vin="JM3KFBCM0L0000003", modelo=base["modelo"], anio=2090, color="Azul", precio=10)
    with pytest.raises(ValidationError):
        v.full_clean()


def test_mantenimiento_costo_negativo(base):
    with pytest.raises(IntegrityError), transaction.atomic():
        Mantenimiento.objects.create(vehiculo=base["veh"], tecnico=base["emp"], descripcion="x", costo=-1)


def test_venta_unica_por_vehiculo(base):
    Venta.objects.create(vehiculo=base["veh"], cliente=base["cli"], empleado=base["emp"], precio_final=1, metodo_pago="contado")
    with pytest.raises(IntegrityError), transaction.atomic():
        Venta.objects.create(vehiculo=base["veh"], cliente=base["cli"], empleado=base["emp"], precio_final=1, metodo_pago="credito")


def test_no_se_borra_vehiculo_con_venta(base):
    Venta.objects.create(vehiculo=base["veh"], cliente=base["cli"], empleado=base["emp"], precio_final=1, metodo_pago="contado")
    with pytest.raises(ProtectedError):
        base["veh"].delete()


def test_no_se_borra_marca_con_modelos(base):
    with pytest.raises(ProtectedError):
        base["marca"].delete()


@pytest.mark.parametrize("valor", [-1, 150])
def test_comision_fuera_de_rango(base, valor):
    # -1 lo frena el CHECK; 150 ya lo frena el tipo DECIMAL(4,2)
    u = get_user_model().objects.create_user("emp2", password="x")
    with pytest.raises((IntegrityError, DataError)), transaction.atomic():
        Empleado.objects.create(user=u, cargo="vendedor", comision_pct=valor)


def test_logout_invalida_refresh(base):
    c = APIClient()
    t = c.post("/api/v1/auth/token/", {"username": "emp", "password": "Clave-De-Prueba-123!"}, format="json").data
    assert c.post("/api/v1/auth/refresh/", {"refresh": t["refresh"]}, format="json").status_code == 200
    # el refresh anterior se rota y queda en lista negra; el ultimo se invalida con logout
    t2 = c.post("/api/v1/auth/token/", {"username": "emp", "password": "Clave-De-Prueba-123!"}, format="json").data
    assert c.post("/api/v1/auth/logout/", {"refresh": t2["refresh"]}, format="json").status_code == 200
    assert c.post("/api/v1/auth/refresh/", {"refresh": t2["refresh"]}, format="json").status_code == 401
    assert c.post("/api/v1/auth/refresh/", {"refresh": t["refresh"]}, format="json").status_code == 401
