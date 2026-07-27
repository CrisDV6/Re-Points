from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import CustomerBalance, PointMovement, User, UserRole
from backend.app.services.auth import require_roles


router = APIRouter(prefix="/client", tags=["Cliente"])


@router.get("/history")
def client_history(
    client: User = Depends(require_roles(UserRole.CLIENT)),
    database: Session = Depends(get_database_session),
) -> dict:
    total_points = database.scalar(
        select(func.coalesce(func.sum(CustomerBalance.points), 0)).where(
            CustomerBalance.user_id == client.id
        )
    )
    movements = database.scalars(
        select(PointMovement)
        .where(PointMovement.user_id == client.id)
        .order_by(PointMovement.created_at.desc())
        .limit(100)
    ).all()
    return {
        "total_points": total_points,
        "movements": [
            {
                "establishment": movement.establishment.name,
                "type": movement.movement_type.value,
                "points": movement.points,
                "description": movement.description,
                "created_at": movement.created_at.isoformat(),
            }
            for movement in movements
        ],
    }
