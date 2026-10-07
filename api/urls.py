from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from . import views

router = DefaultRouter()
router.register("marcas", views.MarcaViewSet)
router.register("modelos", views.ModeloViewSet)
router.register("vehiculos", views.VehiculoViewSet)
router.register("clientes", views.ClienteViewSet)
router.register("empleados", views.EmpleadoViewSet)
router.register("ventas", views.VentaViewSet)
router.register("mantenimientos", views.MantenimientoViewSet)
router.register("auditoria", views.AuditoriaViewSet)

urlpatterns = [
    path("v1/auth/token/", views.LoginView.as_view(), name="token"),
    path("v1/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("v1/auth/logout/", TokenBlacklistView.as_view(), name="token_logout"),
    path("v1/", include(router.urls)),
]

# El esquema y Swagger exponen toda la superficie de la API: solo en desarrollo (M4).
if settings.DEBUG:
    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
