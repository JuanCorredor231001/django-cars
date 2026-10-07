# Informe de seguridad — 2026-10-06

Auditoría del subagente `seguridad` (solo lectura). No se modificó código ni se imprimieron secretos. Las pruebas dinámicas usaron un test temporal fuera del proyecto contra la BD de test. Reemplaza el informe previo del mismo día (el blacklist de refresh tokens y el logout ya figuraban allí como corregidos y esta auditoría los confirma).

## Veredicto: GATE PASS
0 Críticos, 0 Altos, 4 Medios, 6 Bajos (a corregir antes del despliegue).

## Herramientas y pruebas

| Verificación | Resultado |
|---|---|
| `manage.py check --deploy` con `DJANGO_DEBUG=False` | 0 avisos |
| `bandit -r . -x venv,tests` (1173 líneas) | 0 hallazgos |
| `pip-audit` | 8 avisos, todos de `setuptools 57.4.0` del venv (no es dependencia de runtime; corregido en 83.0.0) |
| `.raw(`, `.extra(`, `cursor.execute`, `RawSQL` | 0 coincidencias; solo ORM |
| Throttle de login (8 fallos seguidos) | 401 x5, luego 429 x3 (límite 5/min) |
| Enumeración de usuarios | Misma respuesta 401 para usuario existente e inexistente |
| SQLi (`' OR 1=1 --`, `"; DROP TABLE`, `UNION SELECT`, `%' OR '1'='1`) en `search`, `ordering`, `estado`, `anio`, `modelo` y login | Siempre 200 vacío, 400 o 401; nunca 500, sin datos extra, tabla intacta |
| `pytest tests/test_api.py` / `tests/test_models.py` | 30 passed / 15 passed |
| `pytest` completo en un solo proceso | 45 errors de setup de BD de test (ver B6); no es un fallo de seguridad |

Matriz de roles (GET, tokens reales):

| Recurso | gerente | vendedor | técnico |
|---|---|---|---|
| marcas, modelos, vehiculos | 200 | 200 | 200 |
| clientes, ventas | 200 | 200 | 403 |
| mantenimientos | 200 | 200 | 200 |
| empleados, auditoria | 200 | 403 | 403 |

Controles que cumplen: JWT access 15 min y refresh 8 h con rotación y blacklist (`settings.py:149-154`) y endpoint de logout; Argon2 con PBKDF2 de respaldo y 4 validadores (mínimo 10); `SECRET_KEY` desde `.env`; `DEBUG` por defecto False; cookies Secure, SSL redirect y HSTS con DEBUG=False; CSRF activo; CORS por lista cerrada; contraseñas nunca registradas en auditoría; `permission_classes=[PorCargo]` en todos los ViewSets; `/auditoria/` solo lectura y solo gerente; sin `innerHTML` con datos en el frontend.

## Hallazgos

| Sev. | Hallazgo | Archivo:línea | Corrección propuesta |
|---|---|---|---|
| Medio | **M1.** El vendedor puede borrar clientes y ventas (`DELETE` devuelve 204). Al borrar una venta no se revierte el estado del vehículo y se pierde historial. | `api/views.py:63-67, 78-83` | DELETE solo para gerente (p. ej. `cargos_borrado=(G,)` en `PorCargo`). |
| Medio | **M2.** Un vendedor puede crear o editar ventas con `empleado` de otro y modificar o borrar ventas ajenas (IDOR a nivel de objeto, sin `has_object_permission`). | `api/serializers.py:66-69`, `api/permissions.py:13-23`, `api/views.py:78-83` | Forzar `empleado = request.user.empleado` en `perform_create`, quitarlo de los campos editables para vendedores y filtrar el queryset a sus ventas. |
| Medio | **M3.** El vendedor puede hacer `PATCH vehiculos/<id>` con `estado="vendido"` sin crear la `Venta`, evadiendo la lógica transaccional. | `api/views.py:51-60`, `api/serializers.py:25-33` | `estado` de solo lectura salvo gerente, o que solo cambie vía `Venta`. |
| Medio | **M4.** `/api/schema/` y `/api/docs/` responden 200 sin autenticación. | `api/urls.py:23-24`, `concesionario/settings.py:156-160` | `SERVE_PERMISSIONS` restringido en `SPECTACULAR_SETTINGS` o deshabilitar en producción. |
| Bajo | **B1.** `.env` y `.env.example` traen `DJANGO_DEBUG=True`; la `SECRET_KEY` del `.env` parece un valor real. | `.env:2`, `.env.example:2` | `DJANGO_DEBUG=False` en el ejemplo; generar y rotar secretos para producción. |
| Bajo | **B2.** JWT en `sessionStorage` y sin cabecera CSP. | `frontend/static/frontend/app.js:49-71, 163` | CSP estricta (`django-csp`); valorar refresh en cookie HttpOnly. |
| Bajo | **B3.** Throttle de login solo por IP; sin bloqueo por usuario; `/admin/login/` sin throttle y en ruta por defecto; tras proxy, IP compartida. | `api/views.py:19-21`, `auditoria/middleware.py:28`, `concesionario/urls.py:5` | Límite por usuario (django-axes o throttle propio); IP confiable tras proxy; proteger `/admin/`. |
| Bajo | **B4.** El username de un login fallido entra sin sanear en un log JSON armado a mano (falsificación de logs). | `auditoria/signals.py`, `settings.py:186` | `python-json-logger` o escapar con `repr()`. |
| Bajo | **B5.** El middleware inserta una fila por cada petición `/api/` (también 401/429): un atacante puede inflar la tabla. | `auditoria/middleware.py:31-40` | Política de retención/archivado; no registrar lecturas anónimas repetidas. |
| Bajo | **B6.** setuptools 57.4.0 del venv con 8 CVE; `pytest` completo falla con BD de test compartida; sin tests del 429 ni de la matriz de roles; `requirements.txt` sin versiones fijadas. | `requirements.txt`, `tests/` | `setuptools>=83`; aislar la BD de test; añadir tests; fijar versiones. |

## Resumen
Autenticación, throttle, hashing, SQLi y configuración de despliegue están bien. Lo pendiente es autorización fina (M1 a M3) y exposición del esquema (M4); ninguno es explotable sin una cuenta autenticada, por eso el gate es PASS.

## Estado de remediación (cierre)

| Hallazgo | Estado | Cómo |
|---|---|---|
| M1 vendedor borra clientes/ventas | **Corregido** | `cargos_borrado=(gerente,)` por defecto en `BaseViewSet`; al anular una venta (gerente) el vehículo vuelve a `disponible` |
| M2 IDOR en ventas | **Corregido** | El servidor fija `empleado` según el usuario autenticado; el vendedor solo ve/edita sus ventas (404 en ajenas); no se puede cambiar el vehículo de una venta |
| M3 vendedor marca vehículo vendido | **Corregido** | `estado='vendido'` solo se alcanza registrando una venta; un vendido no se reabre editando |
| M4 `/api/docs` y `/api/schema` públicos | **Corregido** | Solo se publican con `DEBUG=True` |
| B1 `DEBUG=True` en `.env.example` | **Corregido** | Ejemplo en `False`; rotar `SECRET_KEY` y contraseñas en producción |
| B6 setuptools / versiones / tests | **Corregido** | `setuptools>=83` (`pip-audit` sin hallazgos), `requirements.txt` fijado, tests de matriz de roles y 429 añadidos |
| B2 CSP / JWT en sessionStorage | Pendiente (producción) | Añadir `django-csp`; valorar refresh en cookie HttpOnly |
| B3 throttle por usuario, `/admin/` por defecto | Pendiente (producción) | `django-axes` o throttle por usuario; mover/proteger `/admin/` |
| B4 saneado del username en log JSON | Pendiente (bajo) | `python-json-logger` |
| B5 crecimiento de `auditoria_log` | Pendiente (operación) | Política de retención/archivado |

Verificación: 70 tests pasan (`tests/test_autorizacion.py` cubre M1–M4, matriz de roles y 429).
**Veredicto final: GATE PASS** (0 Críticos, 0 Altos, 0 Medios abiertos; 4 Bajos diferidos a producción).
