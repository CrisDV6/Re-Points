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
