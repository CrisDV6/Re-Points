from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_database_session
from backend.app.models.entities import User, UserRole


def get_current_user(
    request: Request,
    database: Session = Depends(get_database_session),
) -> User:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión",
        )

    user = database.get(User, user_id)
    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida",
        )
    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    """Crea una dependencia que limita el acceso según el rol."""

    def validate_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para acceder",
            )
        return user

    return validate_role

