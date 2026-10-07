from django.db import transaction
from rest_framework import serializers, viewsets
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from auditoria.middleware import fijar_usuario
from auditoria.models import AuditoriaLog
from comercial.models import Cliente, Empleado, Venta
from inventario.models import Mantenimiento, Marca, Modelo, Vehiculo

from .permissions import PorCargo, cargo_de
from .serializers import (
    AuditoriaSerializer, ClienteSerializer, EmpleadoSerializer, MantenimientoSerializer,
    MarcaSerializer, ModeloSerializer, VehiculoSerializer, VentaSerializer,
)

G, V, T = "gerente", "vendedor", "tecnico"


class LoginView(TokenObtainPairView):
    throttle_scope = "login"
    throttle_classes = [ScopedRateThrottle]


class FijaUsuarioMixin:
    """Deja el usuario autenticado por JWT disponible para las senales de auditoria."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        fijar_usuario(request.user.get_username() if request.user.is_authenticated else "")


class BaseViewSet(FijaUsuarioMixin, viewsets.ModelViewSet):
    permission_classes = [PorCargo]
    cargos_lectura = None  # None = cualquier empleado autenticado
    cargos_escritura = (G,)
    cargos_borrado = (G,)  # borrar es solo del gerente salvo que la vista diga otra cosa


class MarcaViewSet(BaseViewSet):
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    search_fields = ["nombre", "pais_origen"]


class ModeloViewSet(BaseViewSet):
    queryset = Modelo.objects.select_related("marca")
    serializer_class = ModeloSerializer
    filterset_fields = ["marca", "tipo"]
    search_fields = ["nombre", "marca__nombre"]


class VehiculoViewSet(BaseViewSet):
    queryset = Vehiculo.objects.select_related("modelo__marca")
    serializer_class = VehiculoSerializer
    cargos_escritura = (G, V)
    filterset_fields = {
        "estado": ["exact"], "modelo": ["exact"], "modelo__marca": ["exact"],
        "anio": ["exact", "gte", "lte"], "precio": ["gte", "lte"],
    }
    search_fields = ["vin", "color", "modelo__nombre", "modelo__marca__nombre"]
    ordering_fields = ["precio", "anio", "kilometraje", "fecha_ingreso"]


class ClienteViewSet(BaseViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    cargos_lectura = (G, V)
    cargos_escritura = (G, V)
    search_fields = ["documento", "nombres", "apellidos", "email"]


class EmpleadoViewSet(BaseViewSet):
    queryset = Empleado.objects.select_related("user").order_by("id")
    serializer_class = EmpleadoSerializer
    cargos_lectura = (G,)
    cargos_escritura = (G,)


class VentaViewSet(BaseViewSet):
    queryset = Venta.objects.select_related("vehiculo", "cliente", "empleado")
    serializer_class = VentaSerializer
    cargos_lectura = (G, V)
    cargos_escritura = (G, V)
    filterset_fields = ["cliente", "empleado", "metodo_pago", "fecha"]

    def get_queryset(self):
        qs = super().get_queryset()
        # el vendedor solo ve y toca sus propias ventas (evita IDOR)
        if cargo_de(self.request.user) == V:
            return qs.filter(empleado__user=self.request.user)
        return qs

    def _empleado(self, serializer, instancia=None):
        if cargo_de(self.request.user) == V:
            return self.request.user.empleado  # el vendedor no puede vender a nombre de otro
        emp = serializer.validated_data.get("empleado") or (instancia.empleado if instancia else None)
        emp = emp or getattr(self.request.user, "empleado", None)
        if emp is None:
            raise serializers.ValidationError({"empleado": "Indique el empleado de la venta."})
        return emp

    def perform_create(self, serializer):
        serializer.save(empleado=self._empleado(serializer))

    def perform_update(self, serializer):
        serializer.save(empleado=self._empleado(serializer, serializer.instance))

    @transaction.atomic
    def perform_destroy(self, instance):
        # al anular la venta el vehiculo vuelve al inventario
        vehiculo = instance.vehiculo
        instance.delete()
        vehiculo.estado = vehiculo.Estado.DISPONIBLE
        vehiculo.save(update_fields=["estado"])


class MantenimientoViewSet(BaseViewSet):
    queryset = Mantenimiento.objects.select_related("vehiculo", "tecnico")
    serializer_class = MantenimientoSerializer
    cargos_escritura = (G, T)
    filterset_fields = ["vehiculo", "tecnico"]


class AuditoriaViewSet(FijaUsuarioMixin, viewsets.ReadOnlyModelViewSet):
    """Solo lectura, solo gerentes."""

    permission_classes = [PorCargo]
    cargos_lectura = (G,)
    cargos_escritura = ()
    queryset = AuditoriaLog.objects.all()
    serializer_class = AuditoriaSerializer
    filterset_fields = ["accion", "tabla", "usuario"]
