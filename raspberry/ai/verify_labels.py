import argparse
from pathlib import Path

from raspberry.ai.expert_system import ExpertRules
from raspberry.ai.inference import TFLiteBottleClassifier
from raspberry.ai.preprocessing import validate_image_file


def run() -> None:
    parser = argparse.ArgumentParser(description="Verifica manualmente el mapeo 0/1 del modelo EcoSort AI")
    parser.add_argument("--model", required=True)
    parser.add_argument("--labels", default="raspberry/ai/models/labels.json")
    parser.add_argument("images", nargs="+", help="Imágenes conocidas JPG/PNG de PET y vidrio")
    args = parser.parse_args()
    try:
        import cv2
    except ImportError as exc:
        raise SystemExit("OpenCV no está instalado") from exc
    classifier = TFLiteBottleClassifier(args.model, args.labels, "manual-check", ExpertRules(), require_validated_labels=False)
    print("ADVERTENCIA: este script no valida labels.json automáticamente.")
    for value in args.images:
        path = validate_image_file(value)
        frame = cv2.imread(str(path))
        if frame is None:
            print(f"{path}: no se pudo decodificar")
            continue
        result = classifier.classify(frame)
        print(f"{path.name}: {result.material}, confianza={result.confidence:.4f}")
    print("Confirma visualmente ambos materiales antes de cambiar validated a true.")


if __name__ == "__main__":
    run()
