from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LookupRequestBody(BaseModel):
    appVariant: Literal["christian", "stoic", "dhammapada"]
    anonymizedText: str = Field(min_length=1, max_length=2000)
    sentiment: str = Field(min_length=1, max_length=64)
    emotions: List[str] = Field(default_factory=list, max_length=32)
    confidence: float = Field(ge=0.0, le=100.0)


class ReferenceModel(BaseModel):
    ref: str
    shortReason: str
    text: Optional[str] = None
    translation: Optional[str] = None
    textError: Optional[str] = None


class LookupResult(BaseModel):
    primary: ReferenceModel
    alternates: List[ReferenceModel]
    provider: str
    model: str
    retryCount: int
    fallbackUsed: bool
    crisisFlag: bool
    providersAttempted: List[str] = Field(default_factory=list)

    model_config = {"exclude_none": False}


class StoicStubResult(BaseModel):
    status: Literal["not_implemented"]
    appVariant: Literal["stoic"]
    message: str
    crisisFlag: bool


class LookupUnavailableResult(BaseModel):
    # Returned when crisis hard-exclusion leaves too few eligible passages to
    # answer safely. Not an error — the device renders a gentle empty state.
    status: Literal["lookup_unavailable"]
    appVariant: Literal["dhammapada"]
    message: str
    crisisFlag: bool


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
