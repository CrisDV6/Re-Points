from decimal import Decimal

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.config import AI_ACCEPT_THRESHOLD
from backend.app.models.entities import (
    CustomerBalance,
    Device,
    LocalRewardRule,
    MovementType,
    PointMovement,
    RecyclingEvent,
    User,
    UserRole,
    WasteType,
)
from backend.app.schemas.recycling import DeviceUserValidationRequest, RecyclingEventRequest
from backend.app.services.security import verify_password


router = APIRouter(prefix="/api/recycling-events", tags=["Reciclajes Raspberry"])


def authenticate_device(
    device_code: str,
    api_key: str | None,
    database: Session,
) -> Device:
    device = database.scalar(select(Device).where(Device.device_code == device_code))
    if device is None or api_key is None or not verify_password(api_key, device.api_key_hash):
        raise HTTPException(status_code=401, detail="Credenciales del dispositivo incorrectas")
    if not device.is_active:
        raise HTTPException(status_code=403, detail="El dispositivo está inactivo")
    if not device.establishment.is_active:
        raise HTTPException(status_code=403, detail="El local está inactivo")
    return device


@router.post("/validate-user")
def validate_device_user(
    data: DeviceUserValidationRequest,
    x_device_api_key: str | None = Header(default=None, alias="X-Device-Api-Key"),
    database: Session = Depends(get_database_session),
) -> dict:
    device = authenticate_device(data.deviceId.strip(), x_device_api_key, database)
    user = database.scalar(
        select(User).where(
            User.public_identifier == data.userQrToken.strip(),
            User.role == UserRole.CLIENT,
            User.is_active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario QR no encontrado o inactivo")
    return {
        "success": True,
        "user": {"id": user.id, "name": user.full_name},
        "local": {
            "id": device.establishment.id,
            "name": device.establishment.name,
            "code": device.establishment.code,
        },
    }


@router.post("", status_code=201)
def create_recycling_event(
    data: RecyclingEventRequest,
    x_device_api_key: str | None = Header(default=None, alias="X-Device-Api-Key"),
    database: Session = Depends(get_database_session),
) -> dict:
    device = authenticate_device(data.deviceId.strip(), x_device_api_key, database)
    if data.localId is not None and data.localId != device.establishment_id:
        raise HTTPException(status_code=422, detail="El local no corresponde al dispositivo autenticado")
    if database.scalar(select(RecyclingEvent.id).where(RecyclingEvent.transaction_identifier == data.operationId)):
        raise HTTPException(status_code=409, detail="La operación ya fue registrada")
    if data.captureId and database.scalar(
        select(RecyclingEvent.id).where(RecyclingEvent.capture_identifier == data.captureId)
    ):
        raise HTTPException(status_code=409, detail="La captura ya fue registrada")
    if data.decision != "accepted":
        raise HTTPException(status_code=422, detail="Solo se registran clasificaciones aceptadas")
    if not data.labelsValidated:
        raise HTTPException(status_code=422, detail="El mapeo de etiquetas del modelo no está validado")

    user = database.scalar(select(User).where(User.public_identifier == data.userQrToken.strip(), User.role == UserRole.CLIENT, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario QR no encontrado o inactivo")

    material = WasteType(data.material)
    rule = database.scalar(select(LocalRewardRule).where(LocalRewardRule.establishment_id == device.establishment_id, LocalRewardRule.material == material, LocalRewardRule.is_active.is_(True)))
    if rule is None:
        raise HTTPException(status_code=422, detail="El local no tiene una regla activa para este material")
    confidence = Decimal(str(data.confidence))
    required_confidence = max(Decimal(str(AI_ACCEPT_THRESHOLD)), rule.minimum_confidence)
    if confidence < required_confidence:
        raise HTTPException(status_code=422, detail=f"Confianza insuficiente; el mínimo es {required_confidence}")

    event = RecyclingEvent(
        transaction_identifier=data.operationId,
        user_id=user.id,
        establishment_id=device.establishment_id,
        device_id=device.id,
        waste_type=material,
        bottle_count=1,
        confidence=confidence,
        points_awarded=rule.points,
        accepted=True,
        status="accepted",
        captured_at=data.capturedAt,
        capture_identifier=data.captureId,
        decision=data.decision,
        model_version=data.modelVersion,
        inference_time_ms=Decimal(str(data.inferenceTimeMs)),
    )
    database.add(event)
    database.flush()
    database.add(PointMovement(user_id=user.id, establishment_id=device.establishment_id, recycling_event_id=event.id, movement_type=MovementType.EARNED, points=rule.points, description=f"1 botella de {material.value} registrada por {device.device_code}"))

    balance = database.scalar(select(CustomerBalance).where(CustomerBalance.user_id == user.id, CustomerBalance.establishment_id == device.establishment_id))
    if balance is None:
        balance = CustomerBalance(user_id=user.id, establishment_id=device.establishment_id, points=0, total_points_earned=0, total_points_redeemed=0)
        database.add(balance)
    balance.points += rule.points
    balance.total_points_earned = (balance.total_points_earned or 0) + rule.points
    device.last_connection = data.capturedAt
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="La operación ya fue registrada")

    general_balance = database.scalar(select(func.coalesce(func.sum(CustomerBalance.points), 0)).where(CustomerBalance.user_id == user.id))
    return {
        "success": True,
        "message": "Botella registrada correctamente",
        "eventId": event.id,
        "operationId": data.operationId,
        "local": {"id": device.establishment.id, "name": device.establishment.name, "code": device.establishment.code},
        "material": material.value,
        "tokensEarned": rule.points,
        "localBalance": balance.points,
        "generalBalance": general_balance,
        "decision": event.decision,
        "modelVersion": event.model_version,
        "inferenceTimeMs": float(event.inference_time_ms or 0),
    }


@router.get("/{event_id}")
def get_recycling_event(
    event_id: int,
    device_id: str = Header(alias="X-Device-Id"),
    x_device_api_key: str | None = Header(default=None, alias="X-Device-Api-Key"),
    database: Session = Depends(get_database_session),
) -> dict:
    device = authenticate_device(device_id, x_device_api_key, database)
    event = database.get(RecyclingEvent, event_id)
    if event is None or event.establishment_id != device.establishment_id:
        raise HTTPException(status_code=404, detail="Reciclaje no encontrado")
    return {"id": event.id, "operationId": event.transaction_identifier, "localId": event.establishment_id, "material": event.waste_type.value, "pointsAwarded": event.points_awarded, "status": event.status}
