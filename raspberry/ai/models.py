from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    material: str
    confidence: float
    decision: str
    model_version: str
    inference_time_ms: float
    labels_validated: bool
