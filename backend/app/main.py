from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.app.config import SECRET_KEY, SESSION_COOKIE, SESSION_MAX_AGE
from backend.app.database.session import init_database
from backend.app.routes.auth import router as auth_router
from backend.app.routes.client import router as client_router
from backend.app.routes.locals import router as locals_router
from backend.app.routes.pages import router as pages_router
from backend.app.routes.points import router as points_router
from backend.app.routes.recycling import router as recycling_router
from backend.app.routes.station import router as station_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Re-Points", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie=SESSION_COOKIE,
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)
app.include_router(auth_router)
app.include_router(client_router)
app.include_router(locals_router)
app.include_router(points_router)
app.include_router(recycling_router)
app.include_router(pages_router)
app.include_router(station_router)
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parents[2] / "frontend" / "static"),
    name="static",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Confirma que la aplicación está disponible."""
    return {"status": "ok"}
