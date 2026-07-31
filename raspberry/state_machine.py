from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4
from inspect import signature

from raspberry.ai.expert_system import ExpertRules


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
    def __init__(self, qr_reader, bottle_classifier, api_client, minimum_confidence: float = 0.85, recapture_confidence: float = 0.60):
        self.qr_reader = qr_reader
        self.bottle_classifier = bottle_classifier
        self.api_client = api_client
        self.rules = ExpertRules(minimum_confidence, recapture_confidence)
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
        decision = getattr(classification, "decision", None) or self.rules.decide(classification.confidence).value
        if not getattr(classification, "labels_validated", True):
            self.snapshot.state = StationState.ERROR
            self.snapshot.message = "Etiquetas del modelo sin confirmar; no se asignaron puntos"
            return self.snapshot
        if decision == "recapture":
            self.snapshot.message = "Confianza intermedia; vuelve a colocar la botella para recapturar"
            return self.snapshot
        if decision == "unknown":
            self.snapshot.message = "Material desconocido o sin suficiente confianza; no se asignaron puntos"
            return self.snapshot
        self.snapshot.state = StationState.SUBMITTING
        try:
            event_id = str(uuid4())
            arguments = {
                "operation_id": event_id,
                "user_qr_token": self.snapshot.user_qr_token,
                "material": classification.material,
                "confidence": classification.confidence,
                "captured_at": datetime.now(timezone.utc),
            }
            supported = signature(self.api_client.register_bottle).parameters
            extended = {
                "decision": decision,
                "model_version": getattr(classification, "model_version", "legacy"),
                "inference_time_ms": getattr(classification, "inference_time_ms", 0),
                "capture_id": event_id,
                "labels_validated": getattr(classification, "labels_validated", True),
            }
            arguments.update({key: value for key, value in extended.items() if key in supported})
            result = self.api_client.register_bottle(**arguments)
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
