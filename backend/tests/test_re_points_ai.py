from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from backend.app.database.seed import DEMO_DEVICE_API_KEY
from backend.app.database.session import SessionLocal
from backend.app.models.entities import CustomerBalance, Device, User
from backend.app.services.security import hash_password


HEADERS = {"X-Device-Api-Key": DEMO_DEVICE_API_KEY}


def _context():
    with SessionLocal() as database:
        device = database.scalar(select(Device).where(Device.device_code == "RASPI-ECO-001"))
        device.api_key_hash = hash_password(DEMO_DEVICE_API_KEY)
        database.commit()
        user = database.scalar(select(User).where(User.email == "usuario@repoints.com"))
        balance = database.scalar(select(CustomerBalance).where(CustomerBalance.user_id == user.id, CustomerBalance.establishment_id == device.establishment_id))
        return device.establishment_id, user.public_identifier, balance.points


def _payload(**changes):
    local_id, token, _ = _context()
    event_id = str(uuid4())
    payload = {
        "eventId": event_id,
        "captureId": event_id,
        "deviceId": "RASPI-ECO-001",
        "localId": local_id,
        "userQr": token,
        "material": "plastic",
        "confidence": 0.90,
        "decision": "accepted",
        "modelVersion": "1.0.0",
        "inferenceTimeMs": 145,
        "labelsValidated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(changes)
    return payload


def test_accepted_event_awards_points_once(client):
    _, _, before = _context()
    payload = _payload()
    accepted = client.post("/api/recycling-events", json=payload, headers=HEADERS)
    assert accepted.status_code == 201
    duplicate = client.post("/api/recycling-events", json=payload, headers=HEADERS)
    assert duplicate.status_code == 409
    repeated_capture = dict(payload)
    repeated_capture["eventId"] = str(uuid4())
    assert client.post("/api/recycling-events", json=repeated_capture, headers=HEADERS).status_code == 409
    _, _, after = _context()
    assert after == before + accepted.json()["tokensEarned"]


def test_nonaccepted_decisions_and_unvalidated_labels_never_award(client):
    _, _, before = _context()
    for decision in ("recapture", "unknown"):
        response = client.post("/api/recycling-events", json=_payload(decision=decision), headers=HEADERS)
        assert response.status_code == 422
    unvalidated = client.post("/api/recycling-events", json=_payload(labelsValidated=False), headers=HEADERS)
    assert unvalidated.status_code == 422
    assert _context()[2] == before


def test_controlled_validation_errors(client):
    assert client.post("/api/recycling-events", json=_payload(userQr="missing-user-token"), headers=HEADERS).status_code == 404
    assert client.post("/api/recycling-events", json=_payload(localId=999999), headers=HEADERS).status_code == 422
    assert client.post("/api/recycling-events", json=_payload(deviceId="INVALID-DEVICE"), headers=HEADERS).status_code == 401
    assert client.post("/api/recycling-events", json=_payload(material="metal"), headers=HEADERS).status_code == 422
    assert client.post("/api/recycling-events", json=_payload(), headers={"X-Device-Api-Key": "invalid"}).status_code == 401
