from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.models.entities import QrValidationAttempt, User, UserRole
from backend.app.services.security import hash_password


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


def override_database_session():
    with TestSession() as session:
        yield session


def add_user(database, email: str, role: UserRole, *, active: bool = True) -> User:
    user = User(
        full_name=f"Usuario {role.value}",
        email=email,
        password_hash=hash_password("ClaveSegura123"),
        public_identifier=str(uuid4()),
        role=role,
        is_active=active,
    )
    database.add(user)
    database.commit()
    database.refresh(user)
    return user


def login(client, email: str) -> None:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "ClaveSegura123"},
    )
    assert response.status_code == 200


def test_station_requires_an_administrator(client) -> None:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_database_session] = override_database_session

    try:
        assert client.get("/estacion").status_code == 401
        with TestSession() as database:
            client_user = add_user(database, "client@example.com", UserRole.CLIENT)
        login(client, client_user.email)
        assert client.get("/estacion").status_code == 403
        assert client.post(
            "/station/validate-qr",
            json={"public_identifier": client_user.public_identifier},
        ).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_station_validates_clients_and_audits_attempts(client) -> None:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_database_session] = override_database_session

    try:
        with TestSession() as database:
            admin = add_user(database, "admin@example.com", UserRole.ESTABLISHMENT_ADMIN)
            active_client = add_user(database, "active@example.com", UserRole.CLIENT)
            inactive_client = add_user(
                database, "inactive@example.com", UserRole.CLIENT, active=False
            )

        login(client, admin.email)
        station_page = client.get("/estacion")
        assert station_page.status_code == 200
        assert "Esperando código QR" in station_page.text
        assert "EcoSort AI" in station_page.text
        assert "Material detectado" in station_page.text
        assert "Modo simulación — solo para pruebas" in station_page.text
        assert "archivo .tflite pendiente" in station_page.text
        assert "Asignación de puntos bloqueada" in station_page.text

        server_rendered = client.get(
            "/estacion",
            params={"public_identifier": active_client.public_identifier},
        )
        assert server_rendered.status_code == 200
        assert "CLIENTE AUTORIZADO" in server_rendered.text
        assert active_client.full_name in server_rendered.text

        valid = client.post(
            "/station/validate-qr",
            json={"public_identifier": active_client.public_identifier},
        )
        assert valid.status_code == 200
        assert valid.json()["client"]["full_name"] == active_client.full_name
        assert "email" not in valid.json()["client"]

        assert client.post(
            "/station/validate-qr",
            json={"public_identifier": inactive_client.public_identifier},
        ).status_code == 403
        assert client.post(
            "/station/validate-qr",
            json={"public_identifier": "codigo-inexistente"},
        ).status_code == 404

        with TestSession() as database:
            attempts = database.scalar(select(func.count(QrValidationAttempt.id)))
            successful = database.scalar(
                select(func.count(QrValidationAttempt.id)).where(
                    QrValidationAttempt.successful.is_(True)
                )
            )
        assert attempts == 4
        assert successful == 2
    finally:
        app.dependency_overrides.clear()
