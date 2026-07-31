import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import CustomerBalance, Establishment, PointMovement, RecyclingEvent, Reward, User, UserRole
from backend.app.routes.station import get_operator_establishment
from backend.app.routes.station import validate_qr
from backend.app.schemas.station import QrValidationRequest
from backend.app.services.auth import get_current_user, require_roles
from backend.app.services.qr import generate_qr_data_url


templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def home_page(
    request: Request,
    database: Session = Depends(get_database_session),
) -> HTMLResponse:
    user = database.get(User, request.session.get("user_id")) if request.session.get("user_id") else None
    if user is not None and not user.is_active:
        user = None
    general_balance = 0
    local_count = 0
    if user is not None and user.role == UserRole.CLIENT:
        general_balance = database.scalar(select(func.coalesce(func.sum(CustomerBalance.points), 0)).where(CustomerBalance.user_id == user.id))
        local_count = database.scalar(select(func.count(CustomerBalance.id)).where(CustomerBalance.user_id == user.id))
    return templates.TemplateResponse(request, "home.html", {"user": user, "general_balance": general_balance, "local_count": local_count})


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
    try:
        establishment = get_operator_establishment(operator, database)
    except HTTPException:
        establishment = None
    model_path = Path(os.getenv("AI_MODEL_PATH", "raspberry/ai/models/re_points_mobilenetv2.tflite"))
    labels_path = Path(os.getenv("AI_LABELS_PATH", "raspberry/ai/models/labels.json"))
    labels_validated = False
    try:
        labels_validated = json.loads(labels_path.read_text(encoding="utf-8")).get("validated") is True
    except (OSError, ValueError):
        pass
    mock_mode = os.getenv("AI_MOCK_MODE", "false").lower() in {"1", "true", "yes"}
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
            "establishment": establishment,
            "ai_status": {
                "model_available": model_path.is_file(),
                "labels_validated": labels_validated,
                "mock_mode": mock_mode,
            },
        },
    )


@router.get("/mi-historial", response_class=HTMLResponse)
def history_page(
    request: Request,
    user: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
    localId: int | None = None,
) -> HTMLResponse:
    balance = database.scalar(
        select(func.coalesce(func.sum(CustomerBalance.points), 0)).where(
            CustomerBalance.user_id == user.id
        )
    )
    balances = database.scalars(
        select(CustomerBalance)
        .where(CustomerBalance.user_id == user.id)
        .order_by(CustomerBalance.establishment_id)
    ).all()
    local_cards = []
    for local_balance in balances:
        bottles = database.scalar(
            select(func.coalesce(func.sum(RecyclingEvent.bottle_count), 0)).where(
                RecyclingEvent.user_id == user.id,
                RecyclingEvent.establishment_id == local_balance.establishment_id,
                RecyclingEvent.accepted.is_(True),
            )
        )
        local_cards.append({"balance": local_balance, "bottles": bottles})
    movement_query = select(PointMovement).where(PointMovement.user_id == user.id)
    if localId is not None:
        movement_query = movement_query.where(PointMovement.establishment_id == localId)
    movements = database.scalars(movement_query.order_by(PointMovement.created_at.desc()).limit(100)).all()
    selected_local = database.get(Establishment, localId) if localId is not None else None
    return templates.TemplateResponse(
        request, "history.html", {"user": user, "balance": balance, "local_cards": local_cards, "movements": movements, "selected_local": selected_local}
    )


@router.get("/locales/{local_id}", response_class=HTMLResponse)
def local_detail_page(
    local_id: int,
    request: Request,
    user: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
) -> HTMLResponse:
    local = database.get(Establishment, local_id)
    if local is None or not local.is_active:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Local no encontrado")
    local_balance = database.scalar(select(CustomerBalance).where(CustomerBalance.user_id == user.id, CustomerBalance.establishment_id == local_id))
    bottles = database.scalar(select(func.coalesce(func.sum(RecyclingEvent.bottle_count), 0)).where(RecyclingEvent.user_id == user.id, RecyclingEvent.establishment_id == local_id, RecyclingEvent.accepted.is_(True)))
    events = database.scalars(select(RecyclingEvent).where(RecyclingEvent.user_id == user.id, RecyclingEvent.establishment_id == local_id).order_by(RecyclingEvent.created_at.desc()).limit(20)).all()
    rewards = database.scalars(select(Reward).where(Reward.establishment_id == local_id, Reward.is_active.is_(True)).order_by(Reward.points_required)).all()
    return templates.TemplateResponse(request, "local_detail.html", {"user": user, "local": local, "balance": local_balance.points if local_balance else 0, "bottles": bottles, "events": events, "rewards": rewards})


@router.get("/panel-dueno", response_class=HTMLResponse)
def owner_page(
    request: Request,
    operator: User = Depends(require_roles(UserRole.ESTABLISHMENT_ADMIN, UserRole.SUPERADMIN)),
    database: Session = Depends(get_database_session),
) -> HTMLResponse:
    establishment = get_operator_establishment(operator, database)
    totals = database.execute(
        select(
            func.coalesce(func.sum(RecyclingEvent.bottle_count), 0),
            func.coalesce(func.sum(RecyclingEvent.points_awarded), 0),
            func.count(func.distinct(RecyclingEvent.user_id)),
        ).where(RecyclingEvent.establishment_id == establishment.id)
    ).one()
    events = database.scalars(
        select(RecyclingEvent)
        .where(RecyclingEvent.establishment_id == establishment.id)
        .order_by(RecyclingEvent.created_at.desc())
        .limit(50)
    ).all()
    return templates.TemplateResponse(
        request,
        "owner_dashboard.html",
        {"operator": operator, "establishment": establishment, "totals": totals, "events": events},
    )
