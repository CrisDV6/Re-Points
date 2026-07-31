import time
from pathlib import Path

from raspberry.ai.expert_system import ExpertRules
from raspberry.ai.labels import LabelMapping
from raspberry.ai.models import ClassificationResult
from raspberry.ai.preprocessing import mobilenet_v2_preprocess


class ModelLoadError(RuntimeError):
    pass


def _interpreter_class():
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter
    except ImportError:
        try:
            from tensorflow.lite import Interpreter
            return Interpreter
        except ImportError as exc:
            raise ModelLoadError("Instala tflite-runtime (Raspberry Pi) o TensorFlow") from exc


class TFLiteBottleClassifier:
    def __init__(self, model_path: str, labels_path: str, model_version: str, rules: ExpertRules, require_validated_labels: bool = True) -> None:
        path = Path(model_path)
        if not path.is_file():
            raise ModelLoadError(f"No existe el modelo TensorFlow Lite: {path}")
        self.labels = LabelMapping.load(labels_path)
        if require_validated_labels:
            self.labels.require_validated()
        self.model_version = model_version
        self.rules = rules
        self.interpreter = _interpreter_class()(model_path=str(path))
        self.interpreter.allocate_tensors()
        self.input = self.interpreter.get_input_details()[0]
        self.output = self.interpreter.get_output_details()[0]

    def classify(self, frame) -> ClassificationResult:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("NumPy no está instalado; usa requirements-raspberry.txt") from exc
        tensor = mobilenet_v2_preprocess(frame)
        if tuple(self.input["shape"]) != (1, 224, 224, 3):
            raise RuntimeError(f"Entrada TFLite incompatible: {self.input['shape']}")
        started = time.perf_counter()
        input_tensor = tensor
        if not np.issubdtype(self.input["dtype"], np.floating):
            scale, zero_point = self.input["quantization"]
            if not scale:
                raise RuntimeError("La entrada cuantizada no declara una escala válida")
            input_tensor = np.round(tensor / scale + zero_point)
        self.interpreter.set_tensor(self.input["index"], input_tensor.astype(self.input["dtype"]))
        self.interpreter.invoke()
        raw_tensor = self.interpreter.get_tensor(self.output["index"])
        raw = np.asarray(raw_tensor, dtype=float).reshape(-1)
        if not np.issubdtype(self.output["dtype"], np.floating):
            scale, zero_point = self.output["quantization"]
            if not scale:
                raise RuntimeError("La salida cuantizada no declara una escala válida")
            raw = (raw - zero_point) * scale
        elapsed = (time.perf_counter() - started) * 1000
        if raw.size == 1:
            positive_probability = float(raw[0])
            probabilities = {self.labels.positive_class_index: positive_probability, 1 - self.labels.positive_class_index: 1 - positive_probability}
        elif raw.size == 2:
            total = float(raw.sum())
            probabilities = {0: float(raw[0] / total), 1: float(raw[1] / total)} if total > 0 else {0: 0.5, 1: 0.5}
        else:
            raise RuntimeError("El modelo debe devolver una probabilidad sigmoide o dos probabilidades")
        index = max(probabilities, key=probabilities.get)
        confidence = probabilities[index]
        return ClassificationResult(self.labels.classes[index], confidence, self.rules.decide(confidence).value, self.model_version, elapsed, self.labels.validated)


class MockBottleClassifier:
    def __init__(self, material: str, confidence: float, model_version: str, rules: ExpertRules, enabled: bool) -> None:
        if not enabled:
            raise ModelLoadError("El modo mock solo puede usarse con AI_MOCK_MODE=true")
        if material not in {"plastic", "glass"}:
            raise ValueError("El material mock debe ser plastic o glass")
        self.result = ClassificationResult(material, confidence, rules.decide(confidence).value, f"mock-{model_version}", 0.0, False)

    def classify(self, _frame=None) -> ClassificationResult:
        return self.result
