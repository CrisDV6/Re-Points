from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RecyclingEventRequest(BaseModel):
    operationId: str = Field(min_length=8, max_length=100)
    deviceId: str = Field(min_length=3, max_length=80)
    userQrToken: str = Field(min_length=8, max_length=100)
    material: Literal["plastic", "glass"]
    confidence: float = Field(ge=0, le=1)
    capturedAt: datetime


class DeviceUserValidationRequest(BaseModel):
    deviceId: str = Field(min_length=3, max_length=80)
    userQrToken: str = Field(min_length=8, max_length=100)

