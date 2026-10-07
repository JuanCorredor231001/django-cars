"""Autorizacion fina: hallazgos M1-M4 de la auditoria de seguridad."""
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from comercial.models import Cliente, Venta
from inventario.models import Marca, Modelo, Vehiculo
from tests.test_api import BASE, PWD, cliente_api, crear_usuario


@pytest.fixture
def mundo(db):
    _, eg = crear_usuario("gerente", "gerente")
    _, ev = crear_usuario("vendedor", "vendedor")
    _, ev2 = crear_usuario("vendedor2", "vendedor")
    _, et = crear_usuario("tecnico", "tecnico")
    marca = Marca.objects.create(nombre="Kia")
    modelo = Modelo.objects.create(nombre="Rio", marca=marca)
    vehs = [Vehiculo.objects.create(vin=f"KNADN512{i}A0000001"[:17], modelo=modelo, anio=2022, color="Gris", precio=40_000_000)
            for i in range(3)]
    cli = Cliente.objects.create(documento="55", nombres="Ana", apellidos="Paz")
    return dict(eg=eg, ev=ev, ev2=ev2, et=et, vehs=vehs, cli=cli)


def vender(c, mundo, veh, empleado=None):
    body = {"vehiculo": veh.id, "cliente": mundo["cli"].id, "precio_final": "39000000", "metodo_pago": "contado"}
    if empleado:
        body["empleado"] = empleado.id
    return c.post(BASE + "ventas/", body, format="json")


# --- M1: borrar es solo del gerente ---
@pytest.mark.parametrize("recurso", ["clientes", "vehiculos", "marcas"])
def test_vendedor_no_borra(mundo, recurso):
    c = cliente_api("vendedor")
    pk = {"clientes": mundo["cli"].id, "vehiculos": mundo["vehs"][0].id, "marcas": Marca.objects.first().id}[recurso]
    assert c.delete(f"{BASE}{recurso}/{pk}/").status_code == 403


def test_vendedor_no_borra_venta_y_gerente_si_revierte_estado(mundo):
    v = cliente_api("vendedor")
    r = vender(v, mundo, mundo["vehs"][0])
    assert r.status_code == 201, r.content
    venta_id = r.data["id"]
    assert v.delete(f"{BASE}ventas/{venta_id}/").status_code == 403
    g = cliente_api("gerente")
    assert g.delete(f"{BASE}ventas/{venta_id}/").status_code == 204
    mundo["vehs"][0].refresh_from_db()
    assert mundo["vehs"][0].estado == "disponible"
    assert not Venta.objects.filter(pk=venta_id).exists()


# --- M2: IDOR en ventas ---
def test_vendedor_no_vende_a_nombre_de_otro(mundo):
    c = cliente_api("vendedor")
    r = vender(c, mundo, mundo["vehs"][0], empleado=mundo["ev2"])
    assert r.status_code == 201
    assert Venta.objects.get(pk=r.data["id"]).empleado_id == mundo["ev"].id  # el servidor lo fija


def test_vendedor_no_ve_ni_edita_ventas_ajenas(mundo):
    r = vender(cliente_api("vendedor2"), mundo, mundo["vehs"][1])
    assert r.status_code == 201
    pk = r.data["id"]
    c = cliente_api("vendedor")
    assert c.get(f"{BASE}ventas/{pk}/").status_code == 404
    assert c.patch(f"{BASE}ventas/{pk}/", {"precio_final": "1"}, format="json").status_code == 404
    assert pk not in [x["id"] for x in c.get(BASE + "ventas/").data["results"]]
    assert pk in [x["id"] for x in cliente_api("gerente").get(BASE + "ventas/").data["results"]]


def test_no_se_cambia_el_vehiculo_de_una_venta(mundo):
    c = cliente_api("vendedor")
    pk = vender(c, mundo, mundo["vehs"][0]).data["id"]
    r = c.patch(f"{BASE}ventas/{pk}/", {"vehiculo": mundo["vehs"][1].id}, format="json")
    assert r.status_code == 400


# --- M3: estado 'vendido' solo via venta ---
@pytest.mark.parametrize("usuario", ["vendedor", "gerente"])
def test_no_se_marca_vendido_sin_venta(mundo, usuario):
    c = cliente_api(usuario)
    r = c.patch(f"{BASE}vehiculos/{mundo['vehs'][0].id}/", {"estado": "vendido"}, format="json")
    assert r.status_code == 400
    mundo["vehs"][0].refresh_from_db()
    assert mundo["vehs"][0].estado == "disponible"


def test_vehiculo_vendido_no_se_reabre_editando(mundo):
    vender(cliente_api("vendedor"), mundo, mundo["vehs"][0])
    r = cliente_api("gerente").patch(f"{BASE}vehiculos/{mundo['vehs'][0].id}/", {"estado": "disponible"}, format="json")
    assert r.status_code == 400


def test_reservar_y_liberar_si_se_puede(mundo):
    c = cliente_api("vendedor")
    url = f"{BASE}vehiculos/{mundo['vehs'][2].id}/"
    assert c.patch(url, {"estado": "reservado"}, format="json").status_code == 200
    assert c.patch(url, {"estado": "disponible"}, format="json").status_code == 200


# --- M4: documentacion solo en DEBUG ---
def test_docs_no_publicas_sin_debug(db):
    from django.urls import clear_url_caches, reverse, NoReverseMatch
    import importlib, api.urls, concesionario.urls
    with override_settings(DEBUG=False):
        importlib.reload(api.urls); importlib.reload(concesionario.urls); clear_url_caches()
        assert APIClient().get("/api/docs/").status_code == 404
        assert APIClient().get("/api/schema/").status_code == 404
    importlib.reload(api.urls); importlib.reload(concesionario.urls); clear_url_caches()


# --- matriz de roles (lectura) ---
@pytest.mark.parametrize("usuario,recurso,esperado", [
    ("gerente", "empleados", 200), ("vendedor", "empleados", 403), ("tecnico", "empleados", 403),
    ("gerente", "auditoria", 200), ("vendedor", "auditoria", 403), ("tecnico", "auditoria", 403),
    ("vendedor", "clientes", 200), ("tecnico", "clientes", 403),
    ("vendedor", "ventas", 200), ("tecnico", "ventas", 403),
    ("tecnico", "mantenimientos", 200), ("tecnico", "vehiculos", 200),
])
def test_matriz_roles(mundo, usuario, recurso, esperado):
    assert cliente_api(usuario).get(f"{BASE}{recurso}/").status_code == esperado


# --- throttle de login ---
def test_login_429_tras_5_intentos(db):
    c = APIClient()
    codigos = [c.post(BASE + "auth/token/", {"username": "nadie", "password": "x"}, format="json").status_code for _ in range(7)]
    assert codigos[:5] == [401] * 5
    assert 429 in codigos[5:]
