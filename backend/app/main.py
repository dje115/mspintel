from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=f"{settings.project_name} API",
        version=settings.app_version,
    )

    # In development, also allow any localhost / 127.0.0.1 Vite port so a bad BACKEND_CORS_ORIGINS env
    # cannot brick the UI (browser requires Access-Control-Allow-Origin on API responses).
    dev_local_regex = (
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        if settings.environment == "development"
        else None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend_cors_origins,
        allow_origin_regex=dev_local_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def root_health() -> dict[str, str]:
        return {"status": "ok", "scope": "root"}

    app.include_router(api_router)
    return app


app = create_app()
