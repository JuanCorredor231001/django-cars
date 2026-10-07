"""Crea la BD y los usuarios MySQL con privilegios minimos.

Uso (desde la raiz del proyecto, con el venv activo):
    python scripts/init_db.py --fase 1     # antes de migrate: BD + usuarios
    python manage.py migrate
    python scripts/init_db.py --fase 2     # despues de migrate: permisos sobre auditoria_log

Pide la contrasena de root por consola (getpass); nunca se guarda.
Las contrasenas de los usuarios se leen de .env.
"""
import argparse
import getpass
import sys
from pathlib import Path

import environ
import MySQLdb

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DB = env("DB_NAME")
HOST = env("DB_HOST")
PORT = env.int("DB_PORT")


def usuarios():
    return {
        "admin": (env("DB_ADMIN_USER"), env("DB_ADMIN_PASSWORD")),
        "app": (env("DB_APP_USER"), env("DB_APP_PASSWORD")),
        "ops": (env("DB_OPS_USER"), env("DB_OPS_PASSWORD")),
        "qa": (env("DB_QA_USER"), env("DB_QA_PASSWORD")),
        "audit": (env("DB_AUDIT_USER"), env("DB_AUDIT_PASSWORD")),
    }


def fase1(cur):
    u = usuarios()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    for user, pwd in u.values():
        cur.execute(f"CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (user, pwd))
        cur.execute(f"ALTER USER %s@'%%' IDENTIFIED BY %s", (user, pwd))
    # admin: migraciones (DDL) -> ALL solo sobre la BD del proyecto
    cur.execute(f"GRANT ALL PRIVILEGES ON `{DB}`.* TO %s@'%%'", (u["admin"][0],))
    # admin tambien crea/borra la BD temporal de tests (test_<BD>)
    cur.execute(f"GRANT ALL PRIVILEGES ON `test_{DB}`.* TO %s@'%%'", (u["admin"][0],))
    # app: DML en ejecucion
    cur.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{DB}`.* TO %s@'%%'", (u["app"][0],)
    )
    # ops y qa: SOLO lectura
    cur.execute(f"GRANT SELECT ON `{DB}`.* TO %s@'%%'", (u["ops"][0],))
    cur.execute(f"GRANT SELECT ON `{DB}`.* TO %s@'%%'", (u["qa"][0],))
    # Con binlog activo, MySQL exige SUPER o este flag para crear triggers (auditoria append-only).
    # Ajuste global NO persistente: se pierde al reiniciar MySQL (solo hace falta al migrar).
    cur.execute("SET GLOBAL log_bin_trust_function_creators = 1")
    cur.execute("FLUSH PRIVILEGES")
    print("Fase 1 OK: BD y usuarios creados.")


def fase2(cur):
    u = usuarios()
    # audit: solo lectura sobre la tabla de auditoria
    cur.execute(
        f"GRANT SELECT ON `{DB}`.`auditoria_log` TO %s@'%%'", (u["audit"][0],)
    )
    cur.execute("FLUSH PRIVILEGES")
    print("Fase 2 OK: permisos de auditoria aplicados.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fase", type=int, choices=(1, 2), required=True)
    ap.add_argument("--root-user", default="root")
    args = ap.parse_args()
    pwd = getpass.getpass(f"Contrasena de MySQL '{args.root_user}': ")
    try:
        conn = MySQLdb.connect(host=HOST, port=PORT, user=args.root_user, passwd=pwd)
    except MySQLdb.Error as exc:
        sys.exit(f"No se pudo conectar: {exc}")
    cur = conn.cursor()
    (fase1 if args.fase == 1 else fase2)(cur)
    conn.commit()
    conn.close()
