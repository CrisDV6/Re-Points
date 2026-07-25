from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.models.entities import User


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


def override_database_session():
    with TestSession() as session:
        yield session


def test_registration_login_and_logout(client) -> None:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_database_session] = override_database_session

    registration = client.post(
        "/auth/register",
        json={
            "full_name": "Cliente de Prueba",
            "email": "cliente@example.com",
            "password": "ClaveSegura123",
        },
    )
    assert registration.status_code == 201
    assert registration.json()["user"]["role"] == "client"

    with TestSession() as database:
        user = database.scalar(select(User).where(User.email == "cliente@example.com"))
        assert user is not None
        assert user.password_hash != "ClaveSegura123"

    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401

    wrong_login = client.post(
        "/auth/login",
        json={"email": "cliente@example.com", "password": "incorrecta"},
    )
    assert wrong_login.status_code == 401

    login = client.post(
        "/auth/login",
        json={"email": "cliente@example.com", "password": "ClaveSegura123"},
    )
    assert login.status_code == 200

    duplicate = client.post(
        "/auth/register",
        json={
            "full_name": "Otro Cliente",
            "email": "cliente@example.com",
            "password": "OtraClave123",
        },
    )
    assert duplicate.status_code == 409

    app.dependency_overrides.clear()
