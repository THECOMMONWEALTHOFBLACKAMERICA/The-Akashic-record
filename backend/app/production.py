from __future__ import annotations

from .main import app
from .observability import metrics_middleware, router as metrics_router
from .operations import router as operations_router

# Production-only surfaces are mounted here so the core app remains easy to import in tests.
app.middleware("http")(metrics_middleware)
app.include_router(metrics_router)
app.include_router(operations_router)
