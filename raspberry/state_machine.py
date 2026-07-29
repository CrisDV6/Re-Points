from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class StationState(str, Enum):
    WAITING_QR = "waiting_qr"
    WAITING_BOTTLE = "waiting_bottle"
    SUBMITTING = "submitting"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class StationSnapshot:
    state: StationState = StationState.WAITING_QR
    user_qr_token: str | None = None
    message: str = "Muestra tu código QR"
    last_result: dict | None = None


class RecyclingStation:
    def __init__(self, qr_reader, bottle_classifier, api_client, minimum_confidence: float = 0.80):
        self.qr_reader = qr_reader
        self.bottle_classifier = bottle_classifier
        self.api_client = api_client
        self.minimum_confidence = minimum_confidence
        self.snapshot = StationSnapshot()

    def process_qr_frame(self, frame) -> StationSnapshot:
        if self.snapshot.state != StationState.WAITING_QR:
            return self.snapshot
        token = self.qr_reader.decode(frame)
        if token:
            try:
                validation = self.api_client.validate_user(token)
            except Exception as exc:
                self.snapshot = StationSnapshot(state=StationState.ERROR, message=str(exc))
                return self.snapshot
            self.snapshot = StationSnapshot(
                state=StationState.WAITING_BOTTLE,
                user_qr_token=token,
                message=f"Hola, {validation['user']['name']}. Deposita una botella.",
            )
        return self.snapshot

    def process_bottle_frame(self, frame) -> StationSnapshot:
        if self.snapshot.state != StationState.WAITING_BOTTLE:
            return self.snapshot
        classification = self.bottle_classifier.classify(frame)
        if classification.confidence < self.minimum_confidence:
            self.snapshot.message = "Botella no reconocida con suficiente confianza"
            return self.snapshot
        self.snapshot.state = StationState.SUBMITTING
        try:
            result = self.api_client.register_bottle(
                operation_id=str(uuid4()),
                user_qr_token=self.snapshot.user_qr_token,
                material=classification.material,
                confidence=classification.confidence,
                captured_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            self.snapshot.state = StationState.ERROR
            self.snapshot.message = str(exc)
            return self.snapshot
        self.snapshot.state = StationState.SUCCESS
        self.snapshot.last_result = result
        self.snapshot.message = (
            f"Botella registrada: +{result['tokensEarned']} puntos; "
            f"saldo local {result['localBalance']}"
        )
        return self.snapshot

    def reset(self) -> StationSnapshot:
        self.snapshot = StationSnapshot()
        return self.snapshot
