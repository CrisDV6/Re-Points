from raspberry.bottle_classifier import SimulatedBottleClassifier
from raspberry.state_machine import RecyclingStation, StationState


class FakeQrReader:
    def __init__(self, token=None):
        self.token = token

    def decode(self, _frame):
        return self.token


class FakeApiClient:
    def __init__(self, fail_validation=False):
        self.fail_validation = fail_validation
        self.calls = []

    def validate_user(self, token):
        if self.fail_validation:
            raise RuntimeError("QR inválido")
        return {"user": {"name": "Usuario Demo"}, "token": token}

    def register_bottle(self, operation_id, user_qr_token, material, confidence, captured_at):
        data = {
            "operation_id": operation_id,
            "user_qr_token": user_qr_token,
            "material": material,
            "confidence": confidence,
            "captured_at": captured_at,
        }
        self.calls.append(data)
        return {"tokensEarned": 10, "localBalance": 60}


def test_station_validates_qr_then_registers_bottle():
    api = FakeApiClient()
    station = RecyclingStation(FakeQrReader("qr-demo-token"), SimulatedBottleClassifier(), api)
    assert station.process_qr_frame(None).state == StationState.WAITING_BOTTLE
    result = station.process_bottle_frame(None)
    assert result.state == StationState.SUCCESS
    assert "+10 puntos" in result.message
    assert api.calls[0]["user_qr_token"] == "qr-demo-token"
    assert api.calls[0]["material"] == "plastic"


def test_station_rejects_invalid_qr_and_low_confidence():
    invalid = RecyclingStation(FakeQrReader("bad-token"), SimulatedBottleClassifier(), FakeApiClient(True))
    assert invalid.process_qr_frame(None).state == StationState.ERROR
    low = RecyclingStation(FakeQrReader("good-token"), SimulatedBottleClassifier(confidence=0.4), FakeApiClient())
    low.process_qr_frame(None)
    result = low.process_bottle_frame(None)
    assert result.state == StationState.WAITING_BOTTLE
    assert "suficiente confianza" in result.message
