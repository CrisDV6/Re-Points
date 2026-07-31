from typing import Any


class CameraError(RuntimeError):
    pass


class DualCameraManager:
    """Abre una cámara para QR y otra para la botella."""

    def __init__(self, qr_index: int, bottle_index: int) -> None:
        if qr_index == bottle_index:
            raise ValueError("Las cámaras QR y botella deben usar índices distintos")
        self.qr_index = qr_index
        self.bottle_index = bottle_index
        self._qr_camera: Any = None
        self._bottle_camera: Any = None

    def open(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise CameraError("OpenCV no está instalado; instala requirements-raspberry.txt") from exc
        self._qr_camera = cv2.VideoCapture(self.qr_index)
        self._bottle_camera = cv2.VideoCapture(self.bottle_index)
        if not self._qr_camera.isOpened() or not self._bottle_camera.isOpened():
            self.close()
            raise CameraError(
                f"No fue posible abrir las cámaras {self.qr_index} y {self.bottle_index}"
            )

    def read_qr_frame(self):
        return self._read(self._qr_camera, "QR")

    def read_bottle_frame(self):
        return self._read(self._bottle_camera, "botella")

    @staticmethod
    def _read(camera, label: str):
        if camera is None:
            raise CameraError("Las cámaras todavía no están abiertas")
        ok, frame = camera.read()
        if not ok or frame is None:
            raise CameraError(f"No se pudo leer la cámara de {label}")
        return frame

    def close(self) -> None:
        for camera in (self._qr_camera, self._bottle_camera):
            if camera is not None:
                camera.release()
        self._qr_camera = self._bottle_camera = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *_):
        self.close()
