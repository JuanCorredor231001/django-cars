import logging

from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
import json

from comercial.models import Cliente, Empleado, Venta
from inventario.models import Marca, Mantenimiento, Modelo, Vehiculo

from .middleware import usuario_actual
from .models import AuditoriaLog

log = logging.getLogger("auditoria")
MODELOS = (Marca, Modelo, Vehiculo, Mantenimiento, Cliente, Empleado, Venta)


def _snapshot(instance):
    data = {f.name: getattr(instance, f.attname) for f in instance._meta.concrete_fields}
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))


def _registrar(accion, instance, antes=None, despues=None):
    usuario, ip = usuario_actual()
    AuditoriaLog.objects.create(
        usuario=usuario,
        ip=ip,
        accion=accion,
        tabla=instance._meta.db_table,
        registro_id=str(instance.pk),
        datos_antes=antes,
        datos_despues=despues,
    )


def _conectar():
    for modelo in MODELOS:
        uid = modelo._meta.label_lower

        @receiver(pre_save, sender=modelo, weak=False, dispatch_uid=f"aud_pre_{uid}")
        def _pre(sender, instance, **kw):
            instance._aud_antes = None
            if instance.pk:
                previo = sender.objects.filter(pk=instance.pk).first()
                instance._aud_antes = _snapshot(previo) if previo else None

        @receiver(post_save, sender=modelo, weak=False, dispatch_uid=f"aud_post_{uid}")
        def _post(sender, instance, created, **kw):
            _registrar(
                AuditoriaLog.Accion.CREATE if created else AuditoriaLog.Accion.UPDATE,
                instance,
                antes=getattr(instance, "_aud_antes", None),
                despues=_snapshot(instance),
            )

        @receiver(post_delete, sender=modelo, weak=False, dispatch_uid=f"aud_del_{uid}")
        def _del(sender, instance, **kw):
            _registrar(AuditoriaLog.Accion.DELETE, instance, antes=_snapshot(instance))


_conectar()


@receiver(user_logged_in)
def _login_ok(sender, request, user, **kw):
    AuditoriaLog.objects.create(
        usuario=user.get_username(),
        ip=request.META.get("REMOTE_ADDR") if request else None,
        accion=AuditoriaLog.Accion.LOGIN,
    )


@receiver(user_login_failed)
def _login_fail(sender, credentials, request=None, **kw):
    # nunca se registra la contrasena
    AuditoriaLog.objects.create(
        usuario=str(credentials.get("username", ""))[:150],
        ip=request.META.get("REMOTE_ADDR") if request else None,
        accion=AuditoriaLog.Accion.LOGIN_FAIL,
    )
    log.warning("login fallido usuario=%s", credentials.get("username", ""))
