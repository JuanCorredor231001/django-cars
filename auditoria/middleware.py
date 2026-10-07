import threading

_local = threading.local()

ACCION_POR_METODO = {
    "GET": "READ", "HEAD": "READ", "OPTIONS": "READ",
    "POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE",
}


def usuario_actual():
    return getattr(_local, "usuario", ""), getattr(_local, "ip", None)


def fijar_usuario(nombre):
    """Lo invoca la vista de la API una vez autenticado el JWT."""
    _local.usuario = nombre or ""


class AuditoriaMiddleware:
    """Registra cada peticion a /api/ (usuario, IP, endpoint, codigo de respuesta)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # REMOTE_ADDR: no se confia en X-Forwarded-For sin proxy de confianza.
        _local.ip = request.META.get("REMOTE_ADDR")
        _local.usuario = ""
        response = self.get_response(request)
        if request.path.startswith("/api/") and not request.path.startswith("/api/docs"):
            from .models import AuditoriaLog

            AuditoriaLog.objects.create(
                usuario=_local.usuario,
                ip=_local.ip,
                accion=ACCION_POR_METODO.get(request.method, "READ"),
                endpoint=f"{request.method} {request.path}"[:255],
                status_code=response.status_code,
            )
        return response
