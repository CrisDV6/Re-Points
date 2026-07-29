from dataclasses import dataclass
from math import exp
from pathlib import Path


@dataclass(frozen=True)
class BottleClassification:
    material: str
    confidence: float


class OnnxBottleClassifier:
    """Ejecuta un modelo ONNX con salidas [plastic, glass]."""

    labels = ("plastic", "glass")

    def __init__(self, model_path: str) -> None:
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(f"No existe el modelo de clasificación: {path}")
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV no está instalado") from exc
        self._cv2 = cv2
        self._network = cv2.dnn.readNetFromONNX(str(path))

    def classify(self, frame) -> BottleClassification:
        blob = self._cv2.dnn.blobFromImage(
            frame, scalefactor=1 / 255.0, size=(224, 224), swapRB=True, crop=True
        )
        self._network.setInput(blob)
        raw = self._network.forward().reshape(-1).tolist()
        if len(raw) != len(self.labels):
            raise RuntimeError("El modelo debe devolver dos valores: plastic y glass")
        peak = max(raw)
        probabilities = [exp(value - peak) for value in raw]
        total = sum(probabilities)
        probabilities = [value / total for value in probabilities]
        index = max(range(len(probabilities)), key=probabilities.__getitem__)
        return BottleClassification(self.labels[index], float(probabilities[index]))


class SimulatedBottleClassifier:
    """Clasificador determinista para desarrollar sin cámaras ni modelo."""

    def __init__(self, material: str = "plastic", confidence: float = 0.95) -> None:
        if material not in {"plastic", "glass"}:
            raise ValueError("El material simulado debe ser plastic o glass")
        self.result = BottleClassification(material, confidence)

    def classify(self, _frame=None) -> BottleClassification:
        return self.result
