from pydantic import BaseModel, Field


class QrValidationRequest(BaseModel):
    public_identifier: str = Field(min_length=1, max_length=100)


class ValidatedClientResponse(BaseModel):
    id: int
    full_name: str
    public_identifier: str
    is_active: bool


class QrValidationResponse(BaseModel):
    message: str
    client: ValidatedClientResponse


class BottleDepositRequest(BaseModel):
    public_identifier: str = Field(min_length=1, max_length=100)
    plastic_bottles: int = Field(default=0, ge=0, le=10000)
    glass_bottles: int = Field(default=0, ge=0, le=10000)


class BottleDepositResponse(BaseModel):
    message: str
    client_name: str
    bottle_count: int
    points_awarded: int
    new_balance: int
