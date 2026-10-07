# Concesionario — Django + MySQL + API REST

Plan completo en [PLAN_EJECUCION.md](PLAN_EJECUCION.md). Agentes en `.claude/agents/`.

## Puesta en marcha (PowerShell, desde la raíz)

```powershell
.\venv\Scripts\Activate.ps1

# 1. BD y usuarios MySQL (pide la contraseña de root; no se guarda)
python scripts/init_db.py --fase 1

# 2. Migraciones con el rol admin (DDL)
$env:DB_ROLE = "admin"
python manage.py migrate        # incluye token_blacklist
python scripts/init_db.py --fase 2        # permisos sobre auditoria_log
Remove-Item Env:DB_ROLE                   # volver al rol de aplicación

# 3. Datos demo (usuarios gerente/vendedor/tecnico; contraseña = DEMO_PASSWORD de .env)
python manage.py seed_demo

# 4. Tablas de cache compartida (throttle de login) y tests
$env:DB_ROLE = "admin"; python manage.py createcachetable; Remove-Item Env:DB_ROLE
pytest          # usa concesionario.settings_test (rol admin solo para la BD temporal)

# 5. Servidor con el rol de aplicación (SELECT/INSERT/UPDATE/DELETE)
Remove-Item Env:DB_ROLE
python manage.py runserver
```

- Frontend: http://127.0.0.1:8000/ · Swagger: http://127.0.0.1:8000/api/docs/ (solo con `DJANGO_DEBUG=True`)
- Crear usuarios: `python manage.py crear_empleado --username X --cargo vendedor` (pide la contraseña por consola)
- Reglas: borrar es solo del gerente; el vendedor solo ve y edita sus ventas; `vendido` se alcanza únicamente registrando una venta.
- Secretos solo en `.env` (no versionado); plantilla en `.env.example`.
