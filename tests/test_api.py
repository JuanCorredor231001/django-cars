"""Ejecutar con el rol admin (crea la BD de test):
    $env:DB_ROLE="admin"; pytest
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from auditoria.models import AuditoriaLog
from comercial.models import Cliente, Empleado
from inventario.models import Marca, Modelo, Vehiculo

PWD = "Clave-De-Prueba-123!"
BASE = "/api/v1/"


def crear_usuario(username, cargo):
    u = get_user_model().objects.create_user(username=username, password=PWD)
    emp = Empleado.objects.create(user=u, cargo=cargo)
    return u, emp


def cliente_api(username):
    c = APIClient()
    r = c.post(BASE + "auth/token/", {"username": username, "password": PWD}, format="json")
    assert r.status_code == 200, r.content
    c.credentials(HTTP_AUTHORIZATION="Bearer " + r.data["access"])
    return c


@pytest.fixture
def datos(db):
    g, eg = crear_usuario("gerente", "gerente")
    v, ev = crear_usuario("vendedor", "vendedor")
    t, et = crear_usuario("tecnico", "tecnico")
    marca = Marca.objects.create(nombre="Toyota", pais_origen="Japón")
    modelo = Modelo.objects.create(nombre="Corolla", marca=marca)
    veh = Vehiculo.objects.create(vin="1HGCM82633A000001", modelo=modelo, anio=2022, color="Rojo", precio=50_000_000)
    cli = Cliente.objects.create(documento="123", nombres="Ana", apellidos="Pérez")
    return dict(ev=ev, et=et, eg=eg, veh=veh, cli=cli, marca=marca)


def test_sin_token_401(db):
    assert APIClient().get(BASE + "vehiculos/").status_code == 401


def test_login_incorrecto_no_enumera_usuarios(db):
    crear_usuario("gerente", "gerente")
    a = APIClient().post(BASE + "auth/token/", {"username": "gerente", "password": "x"}, format="json")
    b = APIClient().post(BASE + "auth/token/", {"username": "noexiste", "password": "x"}, format="json")
    assert a.status_code == b.status_code == 401
    assert a.data == b.data


def test_tecnico_no_puede_crear_vehiculo(datos):
    c = cliente_api("tecnico")
    assert c.get(BASE + "vehiculos/").status_code == 200
    r = c.post(BASE + "vehiculos/", {}, format="json")
    assert r.status_code == 403


def test_vendedor_no_ve_empleados_ni_auditoria(datos):
    c = cliente_api("vendedor")
    assert c.get(BASE + "empleados/").status_code == 403
    assert c.get(BASE + "auditoria/").status_code == 403


def test_auditoria_solo_lectura(datos):
    c = cliente_api("gerente")
    assert c.get(BASE + "auditoria/").status_code == 200
    assert c.post(BASE + "auditoria/", {}, format="json").status_code in (403, 405)
    assert c.delete(BASE + "auditoria/1/").status_code in (403, 405)


def test_crud_vehiculo_gerente_y_auditoria(datos):
    c = cliente_api("gerente")
    r = c.post(BASE + "vehiculos/", {
        "vin": "1hgcm82633a000002", "modelo": datos["veh"].modelo_id, "anio": 2021,
        "color": "Azul", "precio": "40000000"}, format="json")
    assert r.status_code == 201, r.content
    pk = r.data["id"]
    assert r.data["vin"] == "1HGCM82633A000002"
    assert c.patch(f"{BASE}vehiculos/{pk}/", {"color": "Negro"}, format="json").status_code == 200
    assert c.delete(f"{BASE}vehiculos/{pk}/").status_code == 204
    acciones = set(AuditoriaLog.objects.filter(tabla="vehiculo", registro_id=str(pk)).values_list("accion", flat=True))
    assert acciones == {"CREATE", "UPDATE", "DELETE"}
    assert AuditoriaLog.objects.filter(tabla="vehiculo", usuario="gerente").exists()


def test_precio_invalido_400(datos):
    c = cliente_api("gerente")
    r = c.post(BASE + "vehiculos/", {
        "vin": "1HGCM82633A000003", "modelo": datos["veh"].modelo_id, "anio": 2021,
        "color": "Azul", "precio": "-5"}, format="json")
    assert r.status_code == 400


def test_venta_marca_vehiculo_vendido_y_no_se_repite(datos):
    c = cliente_api("vendedor")
    payload = {"vehiculo": datos["veh"].id, "cliente": datos["cli"].id, "empleado": datos["ev"].id,
               "precio_final": "48000000", "metodo_pago": "contado"}
    assert c.post(BASE + "ventas/", payload, format="json").status_code == 201
    datos["veh"].refresh_from_db()
    assert datos["veh"].estado == "vendido"
    assert c.post(BASE + "ventas/", payload, format="json").status_code == 400


@pytest.mark.parametrize("payload", ["' OR 1=1 --", "\"; DROP TABLE vehiculo;--", "1 UNION SELECT password FROM auth_user", "%' OR '1'='1"])
@pytest.mark.parametrize("param", ["search", "ordering", "estado", "anio", "modelo"])
def test_sql_injection_en_filtros(datos, payload, param):
    c = cliente_api("gerente")
    r = c.get(BASE + "vehiculos/", {param: payload})
    assert r.status_code in (200, 400), (param, payload, r.status_code)
    if r.status_code == 200:
        assert all("password" not in str(row).lower() for row in r.data["results"])
    # la tabla sigue intacta
    assert Vehiculo.objects.count() == 1


def test_login_con_payload_sqli(db):
    crear_usuario("gerente", "gerente")
    r = APIClient().post(BASE + "auth/token/", {"username": "gerente' OR '1'='1", "password": "' OR '1'='1"}, format="json")
    assert r.status_code == 401


def test_auditoria_log_no_se_modifica_ni_borra(datos):
    log = AuditoriaLog.objects.create(accion="LOGIN", usuario="x")
    with pytest.raises(PermissionError):
        log.delete()
    log.usuario = "otro"
    with pytest.raises(PermissionError):
        log.save()
