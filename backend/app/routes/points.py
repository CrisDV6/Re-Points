from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import CustomerBalance, RecyclingEvent, User, UserRole
from backend.app.services.auth import require_roles


router = APIRouter(prefix="/api/users/me", tags=["Puntos por local"])


def _local_points(balance: CustomerBalance, database: Session) -> dict:
    bottles = database.scalar(
        select(func.coalesce(func.sum(RecyclingEvent.bottle_count), 0)).where(
            RecyclingEvent.user_id == balance.user_id,
            RecyclingEvent.establishment_id == balance.establishment_id,
            RecyclingEvent.accepted.is_(True),
        )
    )
    return {
        "localId": balance.establishment_id,
        "localName": balance.establishment.name,
        "localCode": balance.establishment.code,
        "pointsBalance": balance.points,
        "totalEarned": balance.total_points_earned,
        "totalRedeemed": balance.total_points_redeemed,
        "bottlesRecycled": bottles,
    }


@router.get("/points")
def my_points(
    user: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
) -> dict:
    balances = database.scalars(
        select(CustomerBalance)
        .where(CustomerBalance.user_id == user.id)
        .order_by(CustomerBalance.establishment_id)
    ).all()
    locals_data = [_local_points(balance, database) for balance in balances]
    return {"generalBalance": sum(item["pointsBalance"] for item in locals_data), "locals": locals_data}


@router.get("/points/{local_id}")
def my_local_points(
    local_id: int,
    user: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
) -> dict:
    balance = database.scalar(
        select(CustomerBalance).where(
            CustomerBalance.user_id == user.id,
            CustomerBalance.establishment_id == local_id,
        )
    )
    if balance is None:
        raise HTTPException(status_code=404, detail="No tienes puntos registrados en este local")
    return _local_points(balance, database)


@router.get("/recycling-history")
def my_recycling_history(
    local_id: int | None = Query(default=None, alias="localId"),
    user: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
) -> dict:
    statement = select(RecyclingEvent).where(RecyclingEvent.user_id == user.id)
    if local_id is not None:
        statement = statement.where(RecyclingEvent.establishment_id == local_id)
    events = database.scalars(statement.order_by(RecyclingEvent.created_at.desc()).limit(100)).all()
    return {
        "localId": local_id,
        "events": [
            {
                "id": event.id,
                "localId": event.establishment_id,
                "localName": event.establishment.name,
                "material": event.waste_type.value,
                "bottleCount": event.bottle_count,
                "pointsAwarded": event.points_awarded,
                "createdAt": event.created_at.isoformat(),
            }
            for event in events
        ],
    }
