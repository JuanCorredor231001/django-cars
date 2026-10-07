from django.db import migrations

# auditoria_log es append-only a nivel de motor: ni la app ni nadie puede modificar/borrar filas.
CREAR = [
    """CREATE TRIGGER auditoria_log_no_update BEFORE UPDATE ON auditoria_log
       FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'auditoria_log es append-only'""",
    """CREATE TRIGGER auditoria_log_no_delete BEFORE DELETE ON auditoria_log
       FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'auditoria_log es append-only'""",
]
BORRAR = [
    "DROP TRIGGER IF EXISTS auditoria_log_no_update",
    "DROP TRIGGER IF EXISTS auditoria_log_no_delete",
]


class Migration(migrations.Migration):
    dependencies = [("auditoria", "0001_initial")]
    operations = [migrations.RunSQL(sql=CREAR, reverse_sql=BORRAR)]
