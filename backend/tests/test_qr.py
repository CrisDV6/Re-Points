import base64

import qrcode
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.services.qr import generate_qr_data_url


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=test_engine, expire_on_commit=False)


def override_database_session():
    with TestSession() as session:
        yield session


def test_qr_generator_uses_only_received_identifier(monkeypatch) -> None:
    captured_data = []
    original_add_data = qrcode.QRCode.add_data

    def capture_add_data(self, data, *args, **kwargs):
        captured_data.append(data)
        return original_add_data(self, data, *args, **kwargs)

    monkeypatch.setattr(qrcode.QRCode, "add_data", capture_add_data)
    data_url = generate_qr_data_url("public-id-123")

    assert captured_data == ["public-id-123"]
    assert data_url.startswith("data:image/png;base64,")
    png = base64.b64decode(data_url.split(",", 1)[1])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_qr_page_requires_session_and_renders_personal_qr(client) -> None:
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    app.dependency_overrides[get_database_session] = override_database_session

    try:
        assert client.get("/mi-qr").status_code == 401

        registration = client.post(
            "/auth/register",
            json={
                "full_name": "Cliente QR",
                "email": "qr@example.com",
                "password": "ClaveSegura123",
            },
        )
        public_identifier = registration.json()["user"]["public_identifier"]

        response = client.get("/mi-qr")
        assert response.status_code == 200
        assert "Tu código para reciclar" in response.text
        assert "data:image/png;base64," in response.text
        assert public_identifier not in response.text
        assert "qr@example.com" not in response.text
    finally:
        app.dependency_overrides.clear()
