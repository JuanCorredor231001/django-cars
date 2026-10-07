from django.db import models


class AuditoriaLog(models.Model):
    class Accion(models.TextChoices):
        CREATE = "CREATE"
        READ = "READ"
        UPDATE = "UPDATE"
        DELETE = "DELETE"
        LOGIN = "LOGIN"
        LOGIN_FAIL = "LOGIN_FAIL"

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.CharField(max_length=150, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    accion = models.CharField(max_length=12, choices=Accion.choices)
    tabla = models.CharField(max_length=60, blank=True)
    registro_id = models.CharField(max_length=40, blank=True)
    endpoint = models.CharField(max_length=255, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    datos_antes = models.JSONField(null=True, blank=True)
    datos_despues = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "auditoria_log"
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["accion"]), models.Index(fields=["tabla"])]

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("auditoria_log es append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("auditoria_log es append-only.")
