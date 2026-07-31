import logging
import time
from datetime import datetime


class RePointsApiError(RuntimeError):
    pass


class RePointsApiClient:
    def __init__(self, base_url: str, device_code: str, api_key: str, timeout: float = 10, max_retries: int = 3, pending_queue=None) -> None:
        self.base_url = base_url.rstrip("/")
        self.device_code = device_code
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)
        self.pending_queue = pending_queue

    def validate_user(self, user_qr_token: str) -> dict:
        return self._post(
            "/api/recycling-events/validate-user",
            {"deviceId": self.device_code, "userQrToken": user_qr_token},
        )

    def register_bottle(
        self,
        operation_id: str,
        user_qr_token: str,
        material: str,
        confidence: float,
        captured_at: datetime,
        decision: str = "accepted",
        model_version: str = "legacy",
        inference_time_ms: float = 0,
        capture_id: str | None = None,
        labels_validated: bool = True,
    ) -> dict:
        payload = {
                "operationId": operation_id,
                "deviceId": self.device_code,
                "userQrToken": user_qr_token,
                "material": material,
                "confidence": confidence,
                "capturedAt": captured_at.isoformat(),
                "decision": decision,
                "modelVersion": model_version,
                "inferenceTimeMs": inference_time_ms,
                "captureId": capture_id,
                "labelsValidated": labels_validated,
            }
        try:
            return self._post("/api/recycling-events", payload)
        except RePointsApiError:
            if self.pending_queue is not None:
                self.pending_queue.enqueue(payload)
                self.logger.warning("Evento %s guardado para reenvío", operation_id)
            raise

    def flush_pending(self) -> int:
        if self.pending_queue is None:
            return 0
        remaining = []
        sent = 0
        for event in self.pending_queue.read_all():
            try:
                self._post("/api/recycling-events", event)
                sent += 1
            except RePointsApiError:
                remaining.append(event)
        self.pending_queue.replace(remaining)
        return sent

    def _post(self, path: str, data: dict) -> dict:
        try:
            import requests
        except ImportError as exc:
            raise RePointsApiError("La dependencia requests no está instalada") from exc
        response = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}{path}",
                    headers={"X-Device-Api-Key": self.api_key},
                    json=data,
                    timeout=self.timeout,
                )
                break
            except requests.RequestException as exc:
                if attempt + 1 >= self.max_retries:
                    raise RePointsApiError("Sin conexión con Re-Points; el evento puede reenviarse después") from exc
                self.logger.warning("Fallo de conexión; reintento %s de %s", attempt + 1, self.max_retries)
                time.sleep(0.25 * (2**attempt))
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not response.ok:
            message = payload.get("detail") or "La API rechazó el reciclaje"
            raise RePointsApiError(f"{response.status_code}: {message}")
        return payload
