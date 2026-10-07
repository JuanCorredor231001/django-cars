# Plan de ejecución — Sistema de Concesionario (Django + MySQL + API REST + Agentes)

## 1. Objetivo

Construir una aplicación web para un concesionario de carros con:

- **Backend**: Python 3.10 + Django 5.2 LTS + Django REST Framework (API CRUD).
- **DB**: MySQL 8 (mínimo 5 tablas de negocio + tabla de auditoría).
- **Frontend**: Django Templates + Bootstrap 5 + JS (fetch) consumiendo la API REST.
- **Sistema de agentes** (Claude Code, `.claude/agents/`): 1 orquestador + 4 subagentes (QA DB, Operaciones, Seguridad, Logs).

> Estado del entorno detectado: carpeta vacía, Python 3.10.0 instalado, **cliente MySQL no está en el PATH** → instalar MySQL Server 8 (o usar Docker) en la Fase 0.

---

## 2. Arquitectura

```
                 ┌──────────────────────────────┐
                 │   AGENTE ORQUESTADOR (main)  │
                 │  planifica, delega, consolida│
                 └──────┬───────┬───────┬───────┘
          ┌─────────────┤       │       ├──────────────┐
          ▼             ▼       ▼       ▼              ▼
   ┌───────────┐ ┌───────────┐ ┌────────────┐ ┌──────────────┐
   │ QA  DB    │ │OPERACIONES│ │ SEGURIDAD  │ │ LOGS/HISTÓRICO│
   │ revisa    │ │ solo      │ │ auth + SQLi│ │ auditoría y  │
   │ esquema,  │ │ SELECT    │ │ + OWASP    │ │ reportes     │
   │ integridad│ │ (usuario  │ │            │ │              │
   │           │ │ MySQL RO) │ │            │ │              │
   └─────┬─────┘ └─────┬─────┘ └─────┬──────┘ └──────┬───────┘
         └─────────────┴──────┬──────┴───────────────┘
                              ▼
   Frontend (Templates+JS) ⇄ API REST (DRF, JWT) ⇄ Django ORM ⇄ MySQL 8
```

### Usuarios MySQL (principio de mínimo privilegio)

| Usuario MySQL     | Permisos                                   | Lo usa                         |
|-------------------|--------------------------------------------|--------------------------------|
| `cars_admin`      | ALL sobre `concesionario_db` (migraciones) | Orquestador (solo Fase 1–2)    |
| `cars_app`        | SELECT, INSERT, UPDATE, DELETE             | Aplicación Django en ejecución |
| `cars_ops`        | **SELECT únicamente**                      | Subagente Operaciones          |
| `cars_qa`         | SELECT + `information_schema`              | Subagente QA                   |
| `cars_audit`      | SELECT sobre `auditoria_log`, INSERT en ella | Subagente Logs               |

La restricción "solo SELECT" se aplica **en el motor de BD** (GRANT), no solo en el prompt del agente.

---

## 3. Modelo de datos (7 tablas de negocio + auditoría)

| # | Tabla                | Campos principales                                                                 | Relaciones                  |
|---|----------------------|------------------------------------------------------------------------------------|-----------------------------|
| 1 | `marca`              | id, nombre (único), pais_origen                                                    | —                           |
| 2 | `modelo`             | id, nombre, tipo (sedán/SUV/pickup…), marca_id                                     | FK → marca                  |
| 3 | `vehiculo`           | id, vin (único, 17), modelo_id, anio, color, kilometraje, precio, estado (disponible/reservado/vendido), fecha_ingreso | FK → modelo |
| 4 | `cliente`            | id, documento (único), nombres, apellidos, email, telefono, direccion              | —                           |
| 5 | `empleado`           | id, user_id, cargo (vendedor/gerente/técnico), comision_pct                        | 1:1 → auth_user             |
| 6 | `venta`              | id, vehiculo_id (único), cliente_id, empleado_id, fecha, precio_final, metodo_pago | FK → vehiculo, cliente, empleado |
| 7 | `mantenimiento`      | id, vehiculo_id, fecha, descripcion, costo, tecnico_id                             | FK → vehiculo, empleado     |
| 8 | `auditoria_log`      | id, timestamp, usuario, ip, accion (CREATE/READ/UPDATE/DELETE/LOGIN/LOGIN_FAIL), tabla, registro_id, datos_antes (JSON), datos_despues (JSON) | — |

Reglas de integridad: `CHECK precio > 0`, `anio BETWEEN 1950 AND año_actual+1`, `ON DELETE PROTECT` en ventas, índices en `vin`, `documento`, `estado`, `fecha`. Al registrar una venta → el vehículo pasa a `vendido` dentro de una transacción (`transaction.atomic`).

---

## 4. Estructura del proyecto

```
django_cars/
├── .claude/agents/
│   ├── orquestador.md
│   ├── qa-db.md
│   ├── operaciones.md
│   ├── seguridad.md
│   └── logs-historico.md
├── concesionario/            # proyecto Django (settings, urls)
├── inventario/               # app: marca, modelo, vehiculo, mantenimiento
├── comercial/                # app: cliente, empleado, venta
├── auditoria/                # app: auditoria_log, middleware, señales
├── api/                      # serializers, viewsets, router, permisos
├── frontend/                 # templates + static (Bootstrap, JS)
├── scripts/
│   ├── sql/01_create_db_users.sql
│   ├── qa_checks.sql
│   └── generar_reporte_logs.py
├── tests/
├── .env.example              # credenciales NUNCA en el código
├── requirements.txt
└── manage.py
```

`requirements.txt`: `Django==5.2.*`, `djangorestframework`, `djangorestframework-simplejwt`, `mysqlclient`, `django-environ`, `django-filter`, `drf-spectacular` (Swagger), `bandit`, `pip-audit`, `pytest-django`.

---

## 5. API REST (CRUD)

Base: `/api/v1/` — Router de DRF con `ModelViewSet`:

| Recurso          | Endpoints                                   | Permiso                          |
|------------------|---------------------------------------------|----------------------------------|
| `/marcas/`       | GET, POST, GET/{id}, PUT, PATCH, DELETE     | Lectura: autenticado · Escritura: gerente |
| `/modelos/`      | ídem                                        | ídem                             |
| `/vehiculos/`    | ídem + filtros `?estado=&marca=&precio_max=` | Escritura: vendedor/gerente     |
| `/clientes/`     | ídem + búsqueda `?search=`                  | vendedor/gerente                 |
| `/empleados/`    | ídem                                        | gerente                          |
| `/ventas/`       | ídem (venta marca vehículo como vendido)    | vendedor/gerente                 |
| `/mantenimientos/`| ídem                                       | técnico/gerente                  |
| `/auditoria/`    | **solo GET**                                | gerente                          |
| `/auth/token/`, `/auth/refresh/` | JWT                         | público con rate-limit           |

Documentación automática en `/api/docs/` (Swagger).

---

## 6. Definición de los agentes

### 6.1 Orquestador (agente principal)
- **Rol**: recibe la petición, divide en tareas, delega al subagente correcto, consolida resultados y decide si una fase pasa a la siguiente (*quality gates*).
- **Herramientas**: todas + `Agent` para invocar subagentes.
- **Regla**: no avanza de fase si QA o Seguridad reportan hallazgos **críticos/altos**.

### 6.2 Subagente QA — revisión de la DB
- **Verifica**: que existan las ≥5 tablas, PK/FK, índices, `UNIQUE`, `CHECK`, tipos de datos, nulos indebidos, registros huérfanos, ventas sobre vehículos no `vendido`, duplicados de VIN/documento, migraciones aplicadas (`showmigrations`, `makemigrations --check`).
- **Ejecuta**: `scripts/qa_checks.sql` con usuario `cars_qa` + `pytest` de modelos/API.
- **Salida**: `reports/qa_YYYYMMDD.md` con estado PASS/FAIL por check.

### 6.3 Subagente Operaciones — solo SELECT
- **Rol**: consultas de negocio (inventario disponible, ventas por mes, top vendedores, vehículos con más mantenimiento).
- **Restricción doble**:
  1. Conexión con usuario MySQL `cars_ops` (GRANT SELECT únicamente) → cualquier INSERT/UPDATE/DELETE/DROP falla en el motor.
  2. Prompt + validación: rechaza toda sentencia que no inicie en `SELECT`/`WITH`, y prohíbe `;` múltiples.
- **Herramientas**: Bash (solo para cliente mysql de lectura), Read. Sin Write/Edit.

### 6.4 Subagente Seguridad
- **Autenticación**: JWT con expiración corta, hash Argon2/PBKDF2, validadores de contraseña, bloqueo tras N intentos fallidos (rate-limit DRF `ScopedRateThrottle` en login), `DEBUG=False`, `SECRET_KEY` desde `.env`, cookies `Secure/HttpOnly/SameSite`, CSRF activo, CORS restringido, `ALLOWED_HOSTS`.
- **SQL injection**: busca `raw()`, `cursor.execute` con f-strings/concatenación, `extra()`; exige ORM o consultas parametrizadas; prueba payloads (`' OR 1=1 --`, `UNION SELECT`) contra filtros y búsqueda de la API.
- **Autorización**: verifica que cada ViewSet tenga `permission_classes` y que no haya IDOR.
- **Herramientas**: `python manage.py check --deploy`, `bandit -r .`, `pip-audit`, tests de penetración básicos con `pytest`.
- **Salida**: `reports/seguridad_YYYYMMDD.md` con severidad (Crítico/Alto/Medio/Bajo) y corrección propuesta.

### 6.5 Subagente Logs / Histórico
- **Captura** (implementado en la app `auditoria`):
  - Señales `post_save`/`post_delete` → registra CREATE/UPDATE/DELETE con datos antes/después.
  - Middleware → registra usuario, IP, endpoint, método, código de respuesta.
  - Señales `user_logged_in` / `user_login_failed` → LOGIN / LOGIN_FAIL.
  - `logging` de Django a archivo rotativo `logs/app.log` (JSON).
- **Rol del agente**: genera históricos/reportes (`scripts/generar_reporte_logs.py`): actividad por usuario, cambios por tabla, intentos de login fallidos (alerta a Seguridad), exportación CSV/MD.
- **Regla**: la tabla `auditoria_log` es *append-only* (sin UPDATE/DELETE para nadie salvo admin).

---

## 7. Fases de ejecución

| Fase | Nombre | Responsable | Actividades | Criterio de salida (gate) |
|------|--------|-------------|-------------|---------------------------|
| **0** | Preparación del entorno | Orquestador | Instalar MySQL 8 (o Docker `mysql:8`), crear `venv`, `requirements.txt`, `.env`, `git init` | `python -c "import MySQLdb"` OK y conexión a MySQL OK |
| **1** | Base de datos | Orquestador | `01_create_db_users.sql` (BD + 5 usuarios con GRANTs), proyecto Django, apps, modelos, migraciones, datos semilla (fixtures) | Migraciones aplicadas |
| **2** | ✅ Gate QA #1 | **QA** | Revisión de esquema, integridad, índices, permisos de usuarios MySQL | 0 FAIL críticos |
| **3** | Backend / API REST | Orquestador | Serializers con validación, ViewSets CRUD, permisos por rol, JWT, filtros, Swagger, lógica de venta transaccional | Endpoints responden 200/201/204 |
| **4** | Auditoría y logs | Orquestador + **Logs** | App `auditoria`, señales, middleware, logging a archivo, reporte histórico | Toda operación CRUD y login queda registrada |
| **5** | ✅ Gate Seguridad | **Seguridad** | `check --deploy`, bandit, pip-audit, pruebas SQLi, pruebas de autenticación/autorización | 0 hallazgos Críticos/Altos (si hay → vuelve a Fase 3) |
| **6** | Frontend | Orquestador | Login, dashboard, listados con búsqueda, formularios CRUD por entidad, consumo de API con JWT, escape de HTML (anti-XSS) | Flujo completo desde el navegador |
| **7** | ✅ Gate QA #2 + validación Operaciones | **QA** + **Operaciones** | Tests end-to-end; Operaciones ejecuta consultas de negocio y se verifica que un `INSERT/DELETE` con `cars_ops` **falla** | Tests verdes, ops solo lectura comprobado |
| **8** | Reporte final | **Logs** + Orquestador | Histórico de logs del proceso, consolidado QA + Seguridad, README con instrucciones de despliegue | Entregables completos |

Flujo de control del orquestador:

```
Fase N → subagente gate → ¿PASS? ─sí→ Fase N+1
                              └─no→ devuelve hallazgos → corrige → re-ejecuta gate (máx. 3 iteraciones, luego escala al usuario)
```

---

## 8. Entregables

1. Código Django completo (backend + frontend) y `requirements.txt`.
2. Script SQL de BD y usuarios con privilegios mínimos.
3. API REST documentada en Swagger.
4. 5 definiciones de agentes en `.claude/agents/`.
5. Reportes: `reports/qa_*.md`, `reports/seguridad_*.md`, `reports/historico_logs_*.md`.
6. Suite de pruebas (`pytest`) incluidas pruebas de SQLi y de permisos.
7. `README.md` con instalación y ejecución.

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| `mysqlclient` falla al compilar en Windows | Usar wheel precompilado o `PyMySQL` como fallback (`pymysql.install_as_MySQLdb()`) |
| MySQL no instalado | Docker `mysql:8.0` o instalador MySQL Community |
| Credenciales expuestas | `.env` en `.gitignore`, solo `.env.example` versionado |
| Agente Operaciones intenta escribir | Bloqueado por GRANT en MySQL (defensa en profundidad) |
| Crecimiento de `auditoria_log` | Índice por fecha + archivado mensual por el agente de Logs |

## 10. Decisiones pendientes para el usuario

- ¿MySQL local instalado o vía Docker?
- ¿Frontend con Django Templates (propuesto) o SPA separada (React/Vue)?
- ¿Idioma de nombres de tablas/campos en español (propuesto) o inglés?
