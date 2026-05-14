from dataclasses import dataclass, field
from typing import List, Optional, Protocol


@dataclass
class Reference:
    ref: str
    shortReason: str
    text: Optional[str] = None
    translation: Optional[str] = None
    textError: Optional[str] = None


@dataclass
class LookupResult:
    primary: Reference
    alternates: List[Reference]
    retry_count: int = 0
    fallback_used: bool = False
    # provider/model are populated by the adapter for observability; the
    # variant-routing layer copies them onto the response.
    provider: str = ""
    model: str = ""


@dataclass
class LookupRequest:
    anonymized_text: str
    sentiment: str
    emotions: List[str] = field(default_factory=list)
    confidence: float = 0.0


class LookupAdapter(Protocol):
    app_variant: str

    async def select(self, req: LookupRequest) -> LookupResult: ...
