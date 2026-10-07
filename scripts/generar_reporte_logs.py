"""Genera reports/historico_logs_YYYYMMDD.md desde auditoria_log (usuario cars_audit, solo SELECT).

Uso: python scripts/generar_reporte_logs.py [--desde YYYY-MM-DD] [--hasta YYYY-MM-DD]
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import environ
import MySQLdb

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")


def tabla(titulo, cols, filas):
    out = [f"## {titulo}", ""]
    if not filas:
        return out + ["_Sin datos._", ""]
    out += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in f) + " |" for f in filas]
    return out + [""]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", default=str(date.today() - timedelta(days=7)))
    ap.add_argument("--hasta", default=str(date.today()))
    a = ap.parse_args()
    # Las fechas del CLI son hora de Bogota; la BD guarda UTC (USE_TZ=True).
    bogota = ZoneInfo("America/Bogota")

    def a_utc(d):
        return datetime.fromisoformat(d).replace(tzinfo=bogota).astimezone(timezone.utc).replace(tzinfo=None)

    desde = a_utc(a.desde)  # valida el formato
    hasta = a_utc(a.hasta) + timedelta(days=1)

    conn = MySQLdb.connect(
        host=env("DB_HOST"), port=env.int("DB_PORT"), db=env("DB_NAME"),
        user=env("DB_AUDIT_USER"), passwd=env("DB_AUDIT_PASSWORD"), charset="utf8mb4",
    )
    cur = conn.cursor()
    rango = (desde, hasta)

    def q(sql):
        cur.execute(sql, rango)  # siempre parametrizado
        return cur.fetchall()

    md = [f"# Histórico de logs ({a.desde} → {a.hasta})", "", f"Generado: {datetime.now():%Y-%m-%d %H:%M}", ""]
    md += tabla("Actividad por usuario y acción", ["usuario", "acción", "total"],
                q("SELECT usuario, accion, COUNT(*) FROM auditoria_log WHERE timestamp >= %s AND timestamp < %s "
                  "GROUP BY usuario, accion ORDER BY 3 DESC"))
    md += tabla("Cambios por tabla", ["tabla", "acción", "total"],
                q("SELECT tabla, accion, COUNT(*) FROM auditoria_log WHERE tabla <> '' AND timestamp >= %s AND timestamp < %s "
                  "GROUP BY tabla, accion ORDER BY tabla"))
    fallidos = q("SELECT usuario, ip, COUNT(*), MIN(timestamp), MAX(timestamp) FROM auditoria_log "
                 "WHERE accion = 'LOGIN_FAIL' AND timestamp >= %s AND timestamp < %s GROUP BY usuario, ip ORDER BY 3 DESC")
    md += tabla("Logins fallidos", ["usuario", "ip", "intentos", "primero", "último"], fallidos)
    alertas = [f for f in fallidos if f[2] >= 5]
    if alertas:
        md += ["**ALERTA:** " + ", ".join(f"{f[0] or '(vacío)'}@{f[1]} ({f[2]} intentos)" for f in alertas)
               + " → derivar al agente de seguridad.", ""]
    md += tabla("Respuestas 4xx/5xx por endpoint", ["endpoint", "status", "total"],
                q("SELECT endpoint, status_code, COUNT(*) FROM auditoria_log WHERE status_code >= 400 "
                  "AND timestamp >= %s AND timestamp < %s GROUP BY endpoint, status_code ORDER BY 3 DESC LIMIT 50"))
    md += tabla("Últimos 20 cambios (tabla, id, acción, usuario)", ["fecha", "tabla", "id", "acción", "usuario"],
                q("SELECT timestamp, tabla, registro_id, accion, usuario FROM auditoria_log WHERE tabla <> '' "
                  "AND timestamp >= %s AND timestamp < %s ORDER BY timestamp DESC LIMIT 20"))

    destino = BASE_DIR / "reports" / f"historico_logs_{date.today():%Y%m%d}.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(md), encoding="utf-8")
    print(f"Reporte escrito en {destino}")


if __name__ == "__main__":
    main()
