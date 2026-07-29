from datetime import datetime


class RePointsApiError(RuntimeError):
    pass


class RePointsApiClient:
    def __init__(self, base_url: str, device_code: str, api_key: str, timeout: float = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.device_code = device_code
        self.api_key = api_key
        self.timeout = timeout

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
    ) -> dict:
        return self._post(
            "/api/recycling-events",
            {
                "operationId": operation_id,
                "deviceId": self.device_code,
                "userQrToken": user_qr_token,
                "material": material,
                "confidence": confidence,
                "capturedAt": captured_at.isoformat(),
            },
        )

    def _post(self, path: str, data: dict) -> dict:
        try:
            import requests
        except ImportError as exc:
            raise RePointsApiError("La dependencia requests no está instalada") from exc
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                headers={"X-Device-Api-Key": self.api_key},
                json=data,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise RePointsApiError(f"No se pudo conectar con Re-Points: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not response.ok:
            message = payload.get("detail") or "La API rechazó el reciclaje"
            raise RePointsApiError(f"{response.status_code}: {message}")
        return payload
