import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def limpiar_throttle(db):
    """El throttle de login (5/min) usa la cache (tabla en BD); se limpia entre tests."""
    cache.clear()
    yield
    cache.clear()
