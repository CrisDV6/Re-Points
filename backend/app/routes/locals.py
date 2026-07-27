from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import Establishment, Reward


router = APIRouter(prefix="/api/locals", tags=["Locales"])


def serialize_local(local: Establishment) -> dict:
    return {
        "id": local.id,
        "name": local.name,
        "code": local.code,
        "description": local.description,
        "address": local.address,
        "logoUrl": local.logo_url,
        "active": local.is_active,
        "pointsPerPlasticBottle": local.plastic_points,
        "pointsPerGlassBottle": local.glass_points,
    }


@router.get("")
def public_locals(database: Session = Depends(get_database_session)) -> list[dict]:
    locals_ = database.scalars(
        select(Establishment).where(Establishment.is_active.is_(True)).order_by(Establishment.name)
    ).all()
    return [serialize_local(local) for local in locals_]


@router.get("/{local_id}")
def public_local(local_id: int, database: Session = Depends(get_database_session)) -> dict:
    local = database.get(Establishment, local_id)
    if local is None or not local.is_active:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    return serialize_local(local)


@router.get("/{local_id}/rewards")
def public_local_rewards(local_id: int, database: Session = Depends(get_database_session)) -> list[dict]:
    local = database.get(Establishment, local_id)
    if local is None or not local.is_active:
        raise HTTPException(status_code=404, detail="Local no encontrado")
    rewards = database.scalars(
        select(Reward).where(Reward.establishment_id == local_id, Reward.is_active.is_(True)).order_by(Reward.points_required)
    ).all()
    return [{"id": reward.id, "name": reward.name, "description": reward.description, "pointsRequired": reward.points_required, "stock": reward.available_quantity} for reward in rewards]
