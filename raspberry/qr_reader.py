class QrReader:
    def __init__(self) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV no está instalado") from exc
        self._detector = cv2.QRCodeDetector()

    def decode(self, frame) -> str | None:
        value, _, _ = self._detector.detectAndDecode(frame)
        token = value.strip() if value else ""
        return token or None
