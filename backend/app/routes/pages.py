from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import User, UserRole
from backend.app.routes.station import validate_qr
from backend.app.schemas.station import QrValidationRequest
from backend.app.services.auth import get_current_user, require_roles
from backend.app.services.qr import generate_qr_data_url


templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def home_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "home.html")


@router.get("/registro", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html")


@router.get("/iniciar-sesion", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@router.get("/mi-qr", response_class=HTMLResponse)
def qr_page(
    request: Request,
    user: User = Depends(require_roles(UserRole.CLIENT)),
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "qr.html",
        {"user": user, "qr_data_url": generate_qr_data_url(user.public_identifier)},
    )


@router.get("/estacion", response_class=HTMLResponse)
def station_page(
    request: Request,
    operator: User = Depends(
        require_roles(UserRole.ESTABLISHMENT_ADMIN, UserRole.SUPERADMIN)
    ),
    database: Session = Depends(get_database_session),
    public_identifier: str | None = None,
) -> HTMLResponse:
    validated_client = None
    validation_message = None
    if public_identifier:
        result = validate_qr(
            QrValidationRequest(public_identifier=public_identifier),
            operator,
            database,
        )
        validated_client = result.client
        validation_message = result.message

    return templates.TemplateResponse(
        request,
        "station.html",
        {
            "operator": operator,
            "validated_client": validated_client,
            "validation_message": validation_message,
        },
    )
