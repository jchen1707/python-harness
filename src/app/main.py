"""Build the FastAPI application and its dependencies."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.config import Settings
from app.core.logging import bind_request_context, configure_logging


def create_app(settings: Settings, *, development: bool | None = None) -> FastAPI:
    """Build one application from injected settings."""
    configure_logging(settings.log_level, development=development)
    application = FastAPI()
    application.state.settings = settings
    application.middleware("http")(bind_request_context)
    application.include_router(health_router)
    return application


settings = Settings()  # type: ignore[call-arg]  # BaseSettings supplies fields from its sources.
app = create_app(settings)
