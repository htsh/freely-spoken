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
    providers_attempted: List[str] = field(default_factory=list)  # full chain for load test visibility
    provider_errors: dict = field(default_factory=dict)  # provider -> failure reason for skipped providers


@dataclass
class LookupRequest:
    anonymized_text: str
    sentiment: str
    emotions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    # Informational crisis flag computed by the HTTP layer (app.crisis.check).
    # Stoic ignores it. The Dhammapada adapter uses it to hard-exclude high-risk
    # passages from the LLM-visible index before the prompt is built; the
    # Christian adapter uses it to append a tone/selection guardrail to the
    # system prompt (it has no candidate set to shrink).
    crisis_flag: bool = False


class LookupAdapter(Protocol):
    app_variant: str

    async def select(self, req: LookupRequest) -> LookupResult: ...
