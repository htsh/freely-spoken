import json
import re

import httpx

from app.lookup.base import LookupAdapter, LookupRequest, LookupResult, Reference
from app.providers.gemini import GeminiError, generate as gemini_generate
from app.providers.openrouter import OpenRouterError, generate as openrouter_generate
from app.providers.groq import GroqError, generate as groq_generate

REF_PATTERN = re.compile(r"^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

PROVIDERS = {
    "gemini": ("gemini", "gemini-2.0-flash", gemini_generate),
    "openrouter": ("openrouter", "openrouter/free", openrouter_generate),
    "groq": ("groq", "llama-3.1-8b-instant", groq_generate),
}


def _extract_json(text: str) -> str:
    """Strip markdown code fences and return the inner JSON string."""
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text


def _is_retryable(error: Exception) -> bool:
    cause = getattr(error, "__cause__", None)
    if isinstance(cause, httpx.HTTPStatusError):
        return cause.response.status_code in (429, 500, 502, 503, 504)
    if isinstance(cause, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    return False


CHRISTIAN_SYSTEM_PROMPT = """\
You are a Christian scripture reference selector. Given a person's anonymized emotional situation, select the single most relevant Bible verse reference that would offer comfort, guidance, or perspective, plus two strong alternates.

You must return a JSON object with exactly this structure:
{
  "primary": {"ref": "Book Chapter:Verse", "shortReason": "1-3 sentences"},
  "alternates": [
    {"ref": "Book Chapter:Verse", "shortReason": "1-3 sentences"},
    {"ref": "Book Chapter:Verse", "shortReason": "1-3 sentences"}
  ]
}

Rules:
- Exactly 1 primary verse and exactly 2 alternate verses.
- Reference format: "Book Chapter:Verse" (e.g., "John 3:16", "Psalm 34:18", "1 John 4:18"). No verse text, no chapter ranges.
- shortReason must be 1-3 sentences in plain modern English, no preaching tone.
- Do NOT include the actual verse text — only references and reasons.
- Consider the person's sentiment and emotions when selecting verses.
"""


class ChristianAdapter:
    app_variant = "christian"

    async def select(self, req: LookupRequest) -> LookupResult:
        user_prompt = (
            f"Anonymized text: {req.anonymized_text}\n"
            f"Sentiment: {req.sentiment}\n"
            f"Emotions: {', '.join(req.emotions)}\n"
            f"Confidence: {req.confidence}"
        )

        provider_order = [req.provider]
        if req.fallback:
            for name in PROVIDERS:
                if name != req.provider:
                    provider_order.append(name)

        last_error = None
        for name in provider_order:
            label, model, generate_func = PROVIDERS[name]
            try:
                raw_text, retry_count = await generate_func(
                    CHRISTIAN_SYSTEM_PROMPT, user_prompt
                )

                data = json.loads(_extract_json(raw_text))

                if "primary" not in data or "alternates" not in data:
                    raise GeminiError(
                        f"Missing primary or alternates in response: {data}"
                    )

                primary_data = data["primary"]
                alternates_data = data["alternates"]

                if not isinstance(alternates_data, list) or len(alternates_data) != 2:
                    raise GeminiError(
                        f"Expected exactly 2 alternates, got: {alternates_data}"
                    )

                primary = self._make_reference(primary_data, "primary")
                alternates = [
                    self._make_reference(a, f"alternate[{i}]")
                    for i, a in enumerate(alternates_data)
                ]

                return LookupResult(
                    primary=primary,
                    alternates=alternates,
                    provider=label,
                    model=model,
                    retry_count=retry_count,
                    fallback_used=(name != req.provider),
                )
            except Exception as e:
                last_error = e
                if not _is_retryable(e) or not req.fallback:
                    raise

        raise GeminiError(f"All providers failed. Last error: {last_error}")

    def _make_reference(self, data: dict, label: str) -> Reference:
        if "ref" not in data or "shortReason" not in data:
            raise GeminiError(
                f"Missing ref or shortReason in {label}: {data}"
            )

        ref = data["ref"]
        if not REF_PATTERN.match(ref):
            raise GeminiError(
                f"Invalid ref format in {label}: {ref}"
            )

        short_reason = data["shortReason"]
        sentences = [
            s.strip() for s in short_reason.split(".") if s.strip()
        ]
        if len(sentences) < 1 or len(sentences) > 3:
            raise GeminiError(
                f"shortReason must be 1-3 sentences in {label}: "
                f"{short_reason}"
            )

        return Reference(ref=ref, shortReason=short_reason)
