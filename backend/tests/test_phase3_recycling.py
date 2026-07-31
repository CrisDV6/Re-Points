from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.seed import DEMO_DEVICE_API_KEY, seed_phase_one
from backend.app.database.session import get_database_session
from backend.app.main import app
from backend.app.models.entities import CustomerBalance, Device, RecyclingEvent, User


engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestSession = sessionmaker(bind=engine, expire_on_commit=False)


def override_database():
    with TestSession() as database:
        yield database


def payload(operation="operation-phase3-001", device="RASPI-ECO-001", confidence=0.94):
    with TestSession() as database:
        user = database.scalar(select(User).where(User.email == "usuario@repoints.com"))
        token = user.public_identifier
    return {"operationId": operation, "deviceId": device, "userQrToken": token, "material": "plastic", "confidence": confidence, "capturedAt": datetime.now(timezone.utc).isoformat()}


def test_raspberry_event_awards_only_the_device_local_and_rejects_duplicates(client):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestSession() as database:
        seed_phase_one(database)
    app.dependency_overrides[get_database_session] = override_database
    headers = {"X-Device-Api-Key": DEMO_DEVICE_API_KEY}
    try:
        validation = client.post(
            "/api/recycling-events/validate-user",
            json={"deviceId": "RASPI-ECO-001", "userQrToken": payload()["userQrToken"]},
            headers=headers,
        )
        assert validation.status_code == 200
        assert validation.json()["user"]["name"] == "Usuario Demo"
        assert validation.json()["local"]["code"] == "LOCAL-ECO-001"
        response = client.post("/api/recycling-events", json=payload(), headers=headers)
        assert response.status_code == 201
        result = response.json()
        assert result["local"]["code"] == "LOCAL-ECO-001"
        assert result["tokensEarned"] == 10
        assert result["localBalance"] == 60
        assert result["generalBalance"] == 160
        event_id = result["eventId"]

        duplicate = client.post("/api/recycling-events", json=payload(), headers=headers)
        assert duplicate.status_code == 409
        with TestSession() as database:
            user = database.scalar(select(User).where(User.email == "usuario@repoints.com"))
            balances = {balance.establishment.code: balance.points for balance in database.scalars(select(CustomerBalance).where(CustomerBalance.user_id == user.id)).all()}
            assert balances == {"LOCAL-ECO-001": 60, "LOCAL-GREEN-002": 50, "LOCAL-RECYCLE-003": 50}
            assert database.scalar(select(func.count(RecyclingEvent.id))) == 1

        own_event = client.get(f"/api/recycling-events/{event_id}", headers={"X-Device-Id": "RASPI-ECO-001", **headers})
        assert own_event.status_code == 200
        other_local = client.get(f"/api/recycling-events/{event_id}", headers={"X-Device-Id": "RASPI-GREEN-001", **headers})
        assert other_local.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_raspberry_security_confidence_and_inactive_device(client):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestSession() as database:
        seed_phase_one(database)
    app.dependency_overrides[get_database_session] = override_database
    try:
        assert client.post("/api/recycling-events", json=payload("op-no-key-0001")).status_code == 401
        wrong = client.post("/api/recycling-events", json=payload("op-wrong-key-01"), headers={"X-Device-Api-Key": "incorrecta"})
        assert wrong.status_code == 401
        low = client.post("/api/recycling-events", json=payload("op-low-confidence", confidence=0.4), headers={"X-Device-Api-Key": DEMO_DEVICE_API_KEY})
        assert low.status_code == 422
        with TestSession() as database:
            device = database.scalar(select(Device).where(Device.device_code == "RASPI-ECO-001"))
            device.is_active = False; database.commit()
        inactive = client.post("/api/recycling-events", json=payload("op-inactive-device"), headers={"X-Device-Api-Key": DEMO_DEVICE_API_KEY})
        assert inactive.status_code == 403
        with TestSession() as database:
            assert database.scalar(select(func.count(RecyclingEvent.id))) == 0
    finally:
        app.dependency_overrides.clear()
