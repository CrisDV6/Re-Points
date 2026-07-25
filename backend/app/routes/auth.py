from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import User, UserRole
from backend.app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from backend.app.services.auth import get_current_user
from backend.app.services.security import hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    request: Request,
    database: Session = Depends(get_database_session),
) -> AuthResponse:
    existing_user = database.scalar(select(User).where(User.email == data.email))
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cuenta con ese correo",
        )

    user = User(
        full_name=data.full_name,
        email=data.email,
        password_hash=hash_password(data.password),
        public_identifier=str(uuid4()),
        role=UserRole.CLIENT,
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    request.session["user_id"] = user.id

    return AuthResponse(message="Cuenta creada correctamente", user=UserResponse.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(
    data: LoginRequest,
    request: Request,
    database: Session = Depends(get_database_session),
) -> AuthResponse:
    user = database.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La cuenta está inactiva",
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return AuthResponse(message="Sesión iniciada", user=UserResponse.model_validate(user))


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request) -> MessageResponse:
    request.session.clear()
    return MessageResponse(message="Sesión cerrada")


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)

