from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecyclingEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    operationId: str = Field(min_length=8, max_length=100)
    deviceId: str = Field(min_length=3, max_length=80)
    localId: int | None = Field(default=None, gt=0)
    userQrToken: str = Field(min_length=8, max_length=100)
    material: Literal["plastic", "glass"]
    confidence: float = Field(ge=0, le=1)
    decision: Literal["accepted", "recapture", "unknown"] = "accepted"
    modelVersion: str = Field(default="legacy", min_length=1, max_length=50)
    inferenceTimeMs: float = Field(default=0, ge=0, le=120_000)
    captureId: str | None = Field(default=None, min_length=8, max_length=100)
    labelsValidated: bool = True
    capturedAt: datetime

    @model_validator(mode="before")
    @classmethod
    def normalize_external_contract(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            value.setdefault("operationId", value.get("eventId"))
            value.setdefault("userQrToken", value.get("userQr"))
            value.setdefault("capturedAt", value.get("timestamp"))
        return value


class DeviceUserValidationRequest(BaseModel):
    deviceId: str = Field(min_length=3, max_length=80)
    userQrToken: str = Field(min_length=8, max_length=100)

