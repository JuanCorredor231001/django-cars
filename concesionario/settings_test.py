"""Settings para pytest: la BD temporal `test_<BD>` solo la puede crear el rol admin (DDL).

La aplicacion en ejecucion sigue usando cars_app (sin DDL); esto NO cambia sus privilegios.
"""
from .settings import *  # noqa: F401,F403
from .settings import DATABASES, env

DATABASES["default"]["USER"] = env("DB_ADMIN_USER")
DATABASES["default"]["PASSWORD"] = env("DB_ADMIN_PASSWORD")
