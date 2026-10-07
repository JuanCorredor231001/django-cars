# Resumen final — Concesionario (2026-10-06)

| Fase | Resultado |
|---|---|
| 0 Entorno | venv + Django 5.2 + MySQL 8.0 local |
| 1 BD y usuarios | OK: 5 usuarios MySQL con privilegios mínimos |
| 2 Gate QA | **PASS**: 8 tablas, 8 FK, 5 CHECK, 0 duplicados/huérfanos, `cars_qa` sin escritura (error 1142), triggers append-only verificados con admin |
| 3 API REST | OK: CRUD de 7 recursos + auditoría de solo lectura, JWT, permisos por cargo, venta transaccional |
| 4 Auditoría y logs | OK: señales, middleware, logging a archivo, reporte histórico (`historico_logs_20261006.md`) |
| 5 Gate Seguridad | **PASS**: `check --deploy` sin avisos, bandit y pip-audit sin hallazgos, sin SQL crudo, login 429 tras 5 intentos, SQLi en filtros sin efecto |
| 6 Frontend | OK: panel carga datos con JWT; sin `innerHTML` con datos |
| 7 Tests | **70/70** pasan sin `DB_ROLE` manual (`settings_test`): permisos y matriz de roles, SQLi, venta, auditoría, append-only, modelos, logout/blacklist, 429 y autorización fina |

## Cambios tras la revisión de subagentes
- Gate QA reportó FAIL por `cars_app` sin CREATE (error 1044): es lo esperado; pytest ahora usa `settings_test` (admin solo para la BD temporal). **QA: PASS** (`qa_20261006.md`).
- Seguridad: 2 hallazgos Medios corregidos (blacklist del refresh + logout; caché compartida en BD). **Seguridad: PASS** (`seguridad_20261006.md`).
- Datos demo con 6 ventas y 15 mantenimientos para ejercitar las consultas de Operaciones.

- Segunda auditoría de seguridad (subagentes): 4 Medios (M1–M4) y varios Bajos. Medios y B1/B6 **corregidos y con tests**; Bajos B2–B5 diferidos a producción (ver `seguridad_20261006.md`).

## Pendientes / notas
- Producción: `DJANGO_DEBUG=False`, HTTPS, `SECRET_KEY` propia, rotar contraseñas de `.env`.
- Las cuentas demo (gerente/vendedor/tecnico) deben eliminarse o cambiar de contraseña fuera de desarrollo.
- `SET GLOBAL log_bin_trust_function_creators=1` es temporal (se pierde al reiniciar MySQL).
- Los 5 agentes (`.claude/agents/`) se ejecutaron como subagentes con esos nombres: QA, Seguridad, Operaciones y Logs.
