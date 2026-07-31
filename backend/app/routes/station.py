from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import (
    CustomerBalance,
    Establishment,
    EstablishmentAdmin,
    MovementType,
    PointMovement,
    QrValidationAttempt,
    RecyclingEvent,
    User,
    UserRole,
    WasteType,
)
from backend.app.schemas.station import (
    BottleDepositRequest,
    BottleDepositResponse,
    QrValidationRequest,
    QrValidationResponse,
    ValidatedClientResponse,
)
from backend.app.services.auth import require_roles


router = APIRouter(prefix="/station", tags=["Estación de reciclaje"])
station_operator = require_roles(UserRole.ESTABLISHMENT_ADMIN, UserRole.SUPERADMIN)


def get_operator_establishment(operator: User, database: Session) -> Establishment:
    establishment = database.scalar(
        select(Establishment)
        .join(EstablishmentAdmin)
        .where(
            EstablishmentAdmin.user_id == operator.id,
            Establishment.is_active.is_(True),
        )
    )
    if establishment is None and operator.role == UserRole.SUPERADMIN:
        establishment = database.scalar(
            select(Establishment).where(Establishment.is_active.is_(True)).order_by(Establishment.id)
        )
    if establishment is None:
        raise HTTPException(status_code=403, detail="No tienes un establecimiento activo asignado")
    return establishment


@router.post("/validate-qr", response_model=QrValidationResponse)
def validate_qr(
    data: QrValidationRequest,
    operator: User = Depends(station_operator),
    database: Session = Depends(get_database_session),
) -> QrValidationResponse:
    identifier = data.public_identifier.strip()
    client = database.scalar(
        select(User).where(
            User.public_identifier == identifier,
            User.role == UserRole.CLIENT,
        )
    )

    attempt = QrValidationAttempt(
        operator_id=operator.id,
        matched_user_id=client.id if client else None,
        scanned_identifier=identifier,
        successful=bool(client and client.is_active),
    )
    database.add(attempt)
    database.commit()

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El código QR no corresponde a un cliente",
        )
    if not client.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta del cliente está inactiva",
        )

    return QrValidationResponse(
        message="Cliente identificado correctamente",
        client=ValidatedClientResponse(
            id=client.id,
            full_name=client.full_name,
            public_identifier=client.public_identifier,
            is_active=client.is_active,
        ),
    )


@router.post("/deposits", response_model=BottleDepositResponse, status_code=201)
def register_bottle_deposit(
    data: BottleDepositRequest,
    operator: User = Depends(station_operator),
    database: Session = Depends(get_database_session),
) -> BottleDepositResponse:
    if data.plastic_bottles + data.glass_bottles == 0:
        raise HTTPException(status_code=422, detail="Registra al menos una botella")

    client = database.scalar(
        select(User).where(
            User.public_identifier == data.public_identifier.strip(),
            User.role == UserRole.CLIENT,
            User.is_active.is_(True),
        )
    )
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado o inactivo")

    establishment = get_operator_establishment(operator, database)
    quantities = (
        (WasteType.PLASTIC, data.plastic_bottles, establishment.plastic_points),
        (WasteType.GLASS, data.glass_bottles, establishment.glass_points),
    )
    total_points = 0
    for waste_type, quantity, rate in quantities:
        if quantity == 0:
            continue
        awarded = quantity * rate
        event = RecyclingEvent(
            transaction_identifier=str(uuid4()),
            user_id=client.id,
            establishment_id=establishment.id,
            waste_type=waste_type,
            bottle_count=quantity,
            confidence=1,
            points_awarded=awarded,
            accepted=True,
        )
        database.add(event)
        database.flush()
        database.add(
            PointMovement(
                user_id=client.id,
                establishment_id=establishment.id,
                recycling_event_id=event.id,
                movement_type=MovementType.EARNED,
                points=awarded,
                description=f"{quantity} botella(s) de {waste_type.value}",
            )
        )
        total_points += awarded

    balance = database.scalar(
        select(CustomerBalance).where(
            CustomerBalance.user_id == client.id,
            CustomerBalance.establishment_id == establishment.id,
        )
    )
    if balance is None:
        balance = CustomerBalance(
            user_id=client.id,
            establishment_id=establishment.id,
            points=0,
            total_points_earned=0,
            total_points_redeemed=0,
        )
        database.add(balance)
    balance.points += total_points
    balance.total_points_earned = (balance.total_points_earned or 0) + total_points
    database.commit()

    return BottleDepositResponse(
        message="Botellas registradas y puntos acreditados",
        client_name=client.full_name,
        bottle_count=data.plastic_bottles + data.glass_bottles,
        points_awarded=total_points,
        new_balance=balance.points,
    )


@router.get("/dashboard")
def owner_dashboard(
    operator: User = Depends(station_operator),
    database: Session = Depends(get_database_session),
) -> dict:
    establishment = get_operator_establishment(operator, database)
    totals = database.execute(
        select(
            func.coalesce(func.sum(RecyclingEvent.bottle_count), 0),
            func.coalesce(func.sum(RecyclingEvent.points_awarded), 0),
            func.count(func.distinct(RecyclingEvent.user_id)),
        ).where(
            RecyclingEvent.establishment_id == establishment.id,
            RecyclingEvent.accepted.is_(True),
        )
    ).one()
    recent = database.scalars(
        select(RecyclingEvent)
        .where(RecyclingEvent.establishment_id == establishment.id)
        .order_by(RecyclingEvent.created_at.desc())
        .limit(20)
    ).all()
    return {
        "establishment": establishment.name,
        "total_bottles": totals[0],
        "points_awarded": totals[1],
        "unique_clients": totals[2],
        "recent_events": [
            {
                "client": event.user.full_name,
                "waste_type": event.waste_type.value,
                "bottle_count": event.bottle_count,
                "points": event.points_awarded,
                "created_at": event.created_at.isoformat(),
                "confidence": float(event.confidence),
                "decision": event.decision,
                "model_version": event.model_version,
                "inference_time_ms": float(event.inference_time_ms or 0),
                "local_balance": (
                    database.scalar(
                        select(CustomerBalance.points).where(
                            CustomerBalance.user_id == event.user_id,
                            CustomerBalance.establishment_id == establishment.id,
                        )
                    )
                    or 0
                ),
            }
            for event in recent
        ],
    }
