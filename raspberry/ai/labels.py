import json
from dataclasses import dataclass
from pathlib import Path


class LabelsError(RuntimeError):
    pass


@dataclass(frozen=True)
class LabelMapping:
    classes: dict[int, str]
    validated: bool
    positive_class_index: int

    @classmethod
    def load(cls, path: str | Path) -> "LabelMapping":
        label_path = Path(path)
        if not label_path.is_file():
            raise LabelsError(f"No existe el archivo de etiquetas: {label_path}")
        try:
            data = json.loads(label_path.read_text(encoding="utf-8"))
            classes = {int(index): value for index, value in data["classes"].items()}
            positive = int(data["model_output"]["positive_class_index"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LabelsError(f"labels.json no tiene el formato esperado: {exc}") from exc
        if set(classes.values()) != {"plastic", "glass"} or set(classes) != {0, 1}:
            raise LabelsError("Las etiquetas deben mapear exactamente 0/1 a plastic/glass")
        if positive not in classes:
            raise LabelsError("positive_class_index no existe en classes")
        return cls(classes, data.get("validated") is True, positive)

    def require_validated(self) -> None:
        if not self.validated:
            raise LabelsError(
                "Mapeo de etiquetas sin confirmar. Ejecuta verify_labels.py con imágenes conocidas "
                "y cambia validated a true únicamente después de comprobar el modelo."
            )
