from enum import Enum


class Decision(str, Enum):
    ACCEPTED = "accepted"
    RECAPTURE = "recapture"
    UNKNOWN = "unknown"


class ExpertRules:
    def __init__(self, accept_threshold: float = 0.85, recapture_threshold: float = 0.60) -> None:
        if not 0 <= recapture_threshold < accept_threshold <= 1:
            raise ValueError("Los umbrales deben cumplir 0 <= recaptura < aceptación <= 1")
        self.accept_threshold = accept_threshold
        self.recapture_threshold = recapture_threshold

    def decide(self, confidence: float) -> Decision:
        if not 0 <= confidence <= 1:
            raise ValueError("La confianza debe estar entre 0 y 1")
        if confidence >= self.accept_threshold:
            return Decision.ACCEPTED
        if confidence >= self.recapture_threshold:
            return Decision.RECAPTURE
        return Decision.UNKNOWN
