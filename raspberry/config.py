import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path: Path) -> None:
    """Carga un .env sencillo sin sobrescribir variables ya definidas."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class RaspberryConfig:
    api_base_url: str
    device_code: str
    device_api_key: str
    qr_camera_index: int = 0
    bottle_camera_index: int = 1
    classifier_model_path: str | None = None
    minimum_detection_confidence: float = 0.80
    headless: bool = False
    request_timeout_seconds: float = 10.0

    @classmethod
    def from_environment(cls, env_path: str | Path = "raspberry/.env") -> "RaspberryConfig":
        load_env_file(Path(env_path))
        required = ("REPOINTS_API_URL", "DEVICE_CODE", "DEVICE_API_KEY")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(f"Faltan variables de configuración: {', '.join(missing)}")
        return cls(
            api_base_url=os.environ["REPOINTS_API_URL"].rstrip("/"),
            device_code=os.environ["DEVICE_CODE"],
            device_api_key=os.environ["DEVICE_API_KEY"],
            qr_camera_index=int(os.getenv("QR_CAMERA_INDEX", "0")),
            bottle_camera_index=int(os.getenv("BOTTLE_CAMERA_INDEX", "1")),
            classifier_model_path=os.getenv("CLASSIFIER_MODEL_PATH") or None,
            minimum_detection_confidence=float(os.getenv("MINIMUM_DETECTION_CONFIDENCE", "0.80")),
            headless=os.getenv("HEADLESS", "false").lower() in {"1", "true", "yes"},
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
        )
