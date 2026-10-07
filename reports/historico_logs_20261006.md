# Histórico de logs (2026-09-29 → 2026-10-06)

Generado: 2026-10-06 22:26

## Actividad por usuario y acción

| usuario | acción | total |
|---|---|---|
|  | CREATE | 78 |
| x | LOGIN_FAIL | 5 |
| zz | LOGIN_FAIL | 5 |
| gerente | READ | 4 |
| root | LOGIN_FAIL | 4 |
|  | READ | 2 |

## Cambios por tabla

| tabla | acción | total |
|---|---|---|
| cliente | CREATE | 3 |
| empleado | CREATE | 3 |
| mantenimiento | CREATE | 15 |
| marca | CREATE | 4 |
| modelo | CREATE | 9 |
| vehiculo | CREATE | 18 |
| venta | CREATE | 6 |

## Logins fallidos

| usuario | ip | intentos | primero | último |
|---|---|---|---|---|
| x | 127.0.0.1 | 5 | 2026-10-07 03:02:10.265993 | 2026-10-07 03:02:12.031305 |
| zz | 127.0.0.1 | 5 | 2026-10-07 03:19:09.408812 | 2026-10-07 03:19:11.154177 |
| root | 127.0.0.1 | 4 | 2026-10-07 03:06:22.066267 | 2026-10-07 03:23:32.464352 |

**ALERTA:** x@127.0.0.1 (5 intentos), zz@127.0.0.1 (5 intentos) → derivar al agente de seguridad.

## Respuestas 4xx/5xx por endpoint

| endpoint | status | total |
|---|---|---|
| POST /api/v1/auth/token/ | 401 | 14 |
| POST /api/v1/auth/token/ | 429 | 4 |

## Últimos 20 cambios (tabla, id, acción, usuario)

| fecha | tabla | id | acción | usuario |
|---|---|---|---|---|
| 2026-10-07 03:17:45.611822 | mantenimiento | 15 | CREATE |  |
| 2026-10-07 03:17:45.609822 | mantenimiento | 14 | CREATE |  |
| 2026-10-07 03:17:45.608822 | mantenimiento | 13 | CREATE |  |
| 2026-10-07 03:17:45.607817 | mantenimiento | 12 | CREATE |  |
| 2026-10-07 03:17:45.606456 | mantenimiento | 11 | CREATE |  |
| 2026-10-07 03:17:45.605459 | mantenimiento | 10 | CREATE |  |
| 2026-10-07 03:17:45.603457 | mantenimiento | 9 | CREATE |  |
| 2026-10-07 03:17:45.602456 | mantenimiento | 8 | CREATE |  |
| 2026-10-07 03:17:45.601452 | mantenimiento | 7 | CREATE |  |
| 2026-10-07 03:17:45.599452 | mantenimiento | 6 | CREATE |  |
| 2026-10-07 03:17:45.598452 | mantenimiento | 5 | CREATE |  |
| 2026-10-07 03:17:45.597108 | mantenimiento | 4 | CREATE |  |
| 2026-10-07 03:17:45.596108 | mantenimiento | 3 | CREATE |  |
| 2026-10-07 03:17:45.595108 | mantenimiento | 2 | CREATE |  |
| 2026-10-07 03:17:45.593109 | mantenimiento | 1 | CREATE |  |
| 2026-10-07 03:17:45.590816 | venta | 6 | CREATE |  |
| 2026-10-07 03:17:45.589815 | venta | 5 | CREATE |  |
| 2026-10-07 03:17:45.587815 | venta | 4 | CREATE |  |
| 2026-10-07 03:17:45.586816 | venta | 3 | CREATE |  |
| 2026-10-07 03:17:45.583816 | venta | 2 | CREATE |  |

## Cronología de eventos

**2026-10-06 21:59:59** — Inicio de pruebas (21:59:59-22:00:21)
- Múltiples intentos de acceso no autenticado a `/api/v1/vehiculos/` (401 Unauthorized)
- 2 intentos fallidos de login: usuario "gerente" (contraseña incorrecta) y "noexiste" (usuario no existe)
- Intentos fallidos de acceso a endpoints protegidos `/api/v1/empleados/`, `/api/v1/auditoria/` (403 Forbidden — se requieren permisos específicos)
- ~13 errores 400 Bad Request en `/api/v1/vehiculos/` (consultas malformadas o parámetros inválidos)

**2026-10-06 22:00:03** — Intento de inyección SQL detectado
- Usuario intenta autenticarse con payload de SQLi: `gerente' OR '1'='1`
- El sistema rechaza la autenticación (401 Unauthorized), indicando que los parámetros se tratan como valores, no como código SQL

**2026-10-06 22:02:10—22:02:12** — Ataque de fuerza bruta contra usuario "x"
- 5 intentos fallidos de login en 1.76 segundos (desde 03:02:10 hasta 03:02:12 UTC)
- IP origen: 127.0.0.1 (localhost)
- Tras el 5° intento, el servidor responde con 429 Too Many Requests (rate limiting activo)
- Posteriormente se registran 2 respuestas 429 adicionales (throttle efectivo)

**2026-10-06 22:03:14** — Autenticación exitosa y acceso a recursos
- POST /api/v1/auth/token/ → 200 OK (credenciales correctas)
- GET /api/v1/vehiculos/ → 200 OK (listado de 3657 bytes)
- Intento de SQLi en búsqueda: `?search=' OR 1=1 --` → 200 OK pero respuesta vacía (52 bytes; filtro sanitizado correctamente)
- GET /api/v1/auditoria/?page_size=3 → 200 OK (acceso concedido solo a usuarios autorizados)

**2026-10-06 22:06:10—22:06:27** — Intentos fallidos contra usuario "root"
- 2 intentos fallidos de login en 5.7 segundos
- IP origen: 127.0.0.1
- Respuestas: 401 Unauthorized

**2026-10-06 22:12:50—22:18:48** — Fase de pruebas de seguridad (segunda iteración)
- Ciclo repetido de accesos sin autenticación y errores 400 en búsquedas
- Intentos de SQLi en login: `gerente' OR '1'='1` (rechazados nuevamente)
- Ataques de fuerza bruta contra usuario "g1" (22:14:08): 5 intentos en ~160ms, seguidos de 429 Too Many Requests

**2026-10-06 22:19:09—22:19:11** — Ataque de fuerza bruta contra usuario "zz"
- 5 intentos fallidos de login en 1.74 segundos (desde 03:19:09 hasta 03:19:11 UTC)
- IP origen: 127.0.0.1 (localhost)
- Rate limiting activado: 2 respuestas 429 después del límite

**2026-10-06 22:23:31—22:23:32** — Últimos intentos fallidos contra "root"
- 2 intentos más de login fallido (completando 4 en total para este usuario)
- IP: 127.0.0.1

## Observaciones

### Alertas de seguridad (CRÍTICAS)

**1. Brute Force Attacks Detectados — Usuarios "x" y "zz"**
- Ambos usuarios superan el umbral de 5 intentos fallidos en menos de 10 minutos (de hecho, en ~2 segundos)
- El mecanismo de rate limiting (429 Too Many Requests) se activó correctamente tras el 5° intento
- **Acción recomendada para el agente de seguridad**: Revisar si estas cuentas están habilitadas; si no, confirmar que no son usuarios legítimos. Si lo son, investigar potencial compromiso de credenciales. Considerar incrementar el delay entre intentos de login o implementar CAPTCHA tras 3 fallos.

**2. Intentos de inyección SQL en campo de login**
- Se detectaron payloads de SQLi: `gerente' OR '1'='1`
- **Resultado**: Todos fueron rechazados (401 Unauthorized), indicando que el parámetro se trata como valor, no como código
- **Conclusión**: Las defensas SQL están en lugar (uso de ORM parametrizado). No hay vulnerabilidad explotada.

**3. Intento de SQLi en parámetro de búsqueda**
- Payload: `?search=' OR 1=1 --`
- **Resultado**: 200 OK pero sin datos (respuesta vacía de 52 bytes)
- **Conclusión**: El filtro se implementó correctamente y sanitizó la entrada

### Patrones de errores HTTP

**Errores 401 (Unauthorized) — 14 en total**
- Concentrados en endpoint POST /api/v1/auth/token/
- Causa raíz: credenciales incorrectas o usuario no existe
- Comportamiento esperado

**Errores 429 (Too Many Requests) — 4 en total**
- Resultado directo del rate limiting tras múltiples intentos fallidos de autenticación
- **Evaluación**: El sistema está funcionando como se diseñó (prevención de fuerza bruta efectiva)

**Errores 403 (Forbidden) — Múltiples**
- En endpoints /api/v1/auditoria/ y /api/v1/empleados/
- Causa: Usuario autenticado pero sin permisos para acceder a ese recurso
- Comportamiento esperado (control de acceso basado en roles)

**Errores 400 (Bad Request) — ~13 en total**
- Principalmente en GET /api/v1/vehiculos/
- Causa probable: parámetros de consulta malformados o búsquedas con sintaxis inválida
- No representan un ataque; son errores de validación normales

**Errores 404 (Not Found) — /favicon.ico**
- Errores de cliente (navegador buscando favicon)
- No relevante para la seguridad

### Anomalías detectadas

1. **Usuario vacío en registros de auditoría**: Se registraron 78 operaciones CREATE sin usuario asociado. Esto es consistente con operaciones ejecutadas por el sistema o seed de datos inicial. Verificar que el middleware de auditoría esté capturando correctamente el usuario de la solicitud.

2. **Actividad de lectura baja**: Solo 4 lecturas del usuario "gerente" y 2 sin usuario. En una aplicación concesionaria típica, se esperaría más actividad READ. Puede indicar que el período de reporte es muy corto o que la prueba se enfocó en creaciones.

3. **Concentración de intentos de fuerza bruta desde 127.0.0.1**: Todos los ataques provienen de localhost. En un entorno de producción, multicast atacantes desde IPs externas sería preocupante. En desarrollo/pruebas, esto es normal (testing local).

### Resumen de datos creados

Se registraron 78 operaciones CREATE repartidas entre 7 tablas:
- vehiculo: 18 registros
- mantenimiento: 15 registros
- modelo: 9 registros
- venta: 6 registros
- marca: 4 registros
- cliente: 3 registros
- empleado: 3 registros

Todos los registros CREATE ocurrieron sin usuario, sugiriendo una operación de seed de datos o fixture de prueba.

### Estado de los gates del proyecto

Conforme a resumen_final_20261006.md:
- **Gate QA (Fase 2)**: PASS — 8 tablas, 8 FK, 5 CHECK, triggers append-only verificados
- **Gate Seguridad (Fase 5)**: PASS — 0 Críticos, 0 Altos, 0 Medios abiertos
  - check --deploy: sin avisos
  - bandit, pip-audit: sin hallazgos
  - SQL crudo: 0 casos
  - Login throttle: activo y funcional (429 tras 5 intentos)
  - SQLi en filtros: defendido correctamente

**Conclusión**: Los intentos de ataque registrados en los logs fueron correctamente mitigados por los mecanismos de defensa del sistema. No se detectaron brechas ni accesos exitosos no autorizados.
