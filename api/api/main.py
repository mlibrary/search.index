from api.services import S

if S.app_env != "test":
    # from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.auto_instrumentation import initialize

    initialize()

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import fastapi_structured_logging

from .routers import catalog
from .routers import onlinejournals
from .routers import articles


app = FastAPI(
    title="Catalog Search API", description="REST API for Catalog Search Solr"
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(fastapi_structured_logging.AccessLogMiddleware)
app.include_router(catalog.router)
app.include_router(onlinejournals.router)
app.include_router(articles.router)

Instrumentator().instrument(app).expose(app)
# FastAPIInstrumentor.instrument_app(app)
