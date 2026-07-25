from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.database.base import Base
from backend.app.models.entities import EstablishmentAdmin, UserRole
from backend.scripts.create_station_admin import create_station_admin


def test_create_station_admin_is_repeatable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as database:
        establishment, user = create_station_admin(
            database,
            "Eco Mercado",
            "Administrador Local",
            "ADMIN@EXAMPLE.COM",
            "ClaveSegura123",
        )
        repeated_establishment, repeated_user = create_station_admin(
            database,
            "Eco Mercado",
            "Administrador Local",
            "admin@example.com",
            "ClaveSegura123",
        )

        assert user.role == UserRole.ESTABLISHMENT_ADMIN
        assert user.email == "admin@example.com"
        assert repeated_user.id == user.id
        assert repeated_establishment.id == establishment.id
        assignments = database.scalar(select(func.count(EstablishmentAdmin.id)))
        assert assignments == 1
