import json
import re

import httpx

from app.lookup.base import LookupAdapter, LookupRequest, LookupResult, Reference
from app.providers.gemini import GeminiError, generate as gemini_generate
from app.providers.openrouter import OpenRouterError, generate as openrouter_generate

REF_PATTERN = re.compile(r"^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$")

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

        provider = "gemini"
        model = "gemini-2.0-flash"
        fallback_used = False
        retry_count = 0

        try:
            raw_text, retry_count = await gemini_generate(
                CHRISTIAN_SYSTEM_PROMPT, user_prompt
            )
        except GeminiError as e:
            cause = getattr(e, "__cause__", None)
            if (
                isinstance(cause, httpx.HTTPStatusError)
                and cause.response.status_code == 429
            ):
                try:
                    raw_text = await openrouter_generate(
                        CHRISTIAN_SYSTEM_PROMPT, user_prompt
                    )
                    provider = "openrouter"
                    model = "openrouter/free"
                    fallback_used = True
                    retry_count = 0
                except OpenRouterError as oe:
                    raise GeminiError(
                        "Gemini rate-limited (3 retries), "
                        f"OpenRouter also failed: {oe}"
                    ) from oe
            else:
                raise

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise GeminiError(
                f"Invalid JSON from Gemini: {e}\nText: {raw_text[:500]}"
            ) from e

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
            provider=provider,
            model=model,
            retry_count=retry_count,
            fallback_used=fallback_used,
        )

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
