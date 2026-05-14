from dataclasses import dataclass
from typing import List, Optional, Protocol


@dataclass
class Reference:
    ref: str
    shortReason: str
    # Canonical text fetched from a variant-specific source (e.g. bible-api.com
    # for Christian). Optional because the LLM step produces a usable Reference
    # on its own; enrichment is best-effort and may fail independently.
    text: Optional[str] = None
    translation: Optional[str] = None
    text_error: Optional[str] = None


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
