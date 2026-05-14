from dataclasses import dataclass
from typing import List, Protocol


@dataclass
class Reference:
    ref: str
    shortReason: str


@dataclass
class LookupResult:
    primary: Reference
    alternates: List[Reference]
    provider: str
    model: str
    retry_count: int = 0
    fallback_used: bool = False


@dataclass
class LookupRequest:
    anonymized_text: str
    sentiment: str
    emotions: List[str]
    confidence: str
    provider: str = "gemini"
    fallback: bool = True


class LookupAdapter(Protocol):
    app_variant: str

    async def select(self, req: LookupRequest) -> LookupResult:
        ...
