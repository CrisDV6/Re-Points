from pathlib import Path

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def validate_image_file(path: str | Path) -> Path:
    image_path = Path(path)
    if not image_path.is_file():
        raise ValueError(f"No existe la imagen: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise ValueError("Formato no permitido; usa JPG, JPEG o PNG")
    if image_path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("La imagen supera el límite de 10 MB")
    return image_path


def mobilenet_v2_preprocess(frame):
    """Convierte BGR/RGB a un batch RGB 224x224 y aplica x/127.5 - 1."""
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("NumPy no está instalado; usa requirements-raspberry.txt") from exc
    if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("La captura debe ser una imagen de color con tres canales")
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("OpenCV no está instalado") from exc
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, (224, 224), interpolation=cv2.INTER_AREA)
    normalized = resized.astype(np.float32) / 127.5 - 1.0
    return np.expand_dims(normalized, axis=0)
