from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import QrValidationAttempt, User, UserRole
from backend.app.schemas.station import (
    QrValidationRequest,
    QrValidationResponse,
    ValidatedClientResponse,
)
from backend.app.services.auth import require_roles


router = APIRouter(prefix="/station", tags=["Estación de reciclaje"])
station_operator = require_roles(UserRole.ESTABLISHMENT_ADMIN, UserRole.SUPERADMIN)


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
