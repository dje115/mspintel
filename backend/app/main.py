from fastapi import FastAPI

from app.api.router import api_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.project_name} API",
        version="0.1.0",
    )

    @app.get("/health", tags=["health"])
    def root_health() -> dict[str, str]:
        return {"status": "ok", "scope": "root"}

    app.include_router(api_router)
    return app


app = create_app()
