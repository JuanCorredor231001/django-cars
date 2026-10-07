from rest_framework.permissions import SAFE_METHODS, BasePermission


def cargo_de(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser:
        return "gerente"
    empleado = getattr(user, "empleado", None)
    return empleado.cargo if empleado else None


class PorCargo(BasePermission):
    """Lectura: cargos en `cargos_lectura` (None = cualquier empleado).
    Escritura: solo los cargos en `cargos_escritura`.
    Borrado: solo los cargos en `cargos_borrado` (por defecto, igual que escritura)."""

    def has_permission(self, request, view):
        cargo = cargo_de(request.user)
        if cargo is None:
            return False
        if request.method in SAFE_METHODS:
            return view.cargos_lectura is None or cargo in view.cargos_lectura
        if request.method == "DELETE":
            return cargo in getattr(view, "cargos_borrado", view.cargos_escritura)
        return cargo in view.cargos_escritura
