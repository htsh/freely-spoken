import asyncio
import json
import re

import httpx

from app.lookup.base import LookupAdapter, LookupRequest, LookupResult, Reference
from app.lookup.bible_api import BibleApiError, fetch_verse
from app.providers.gemini import GeminiError, generate as gemini_generate
from app.providers.openrouter import OpenRouterError, generate as openrouter_generate
from app.providers.groq import GroqError, generate as groq_generate

REF_PATTERN = re.compile(r"^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
# Catches obvious cases where the model dumps a long scripture-style quotation
# into shortReason. Not foolproof — three sentences is the harder cap.
_SCRIPTURE_HINTS = re.compile(
    r'"[^"]{120,}"|saith the LORD|verily I say|thus says the Lord',
    re.IGNORECASE,
)

PROVIDERS = {
    "gemini": ("gemini", "gemini-2.0-flash", gemini_generate),
    "openrouter": ("openrouter", "openrouter/free", openrouter_generate),
    "groq": ("groq", "llama-3.1-8b-instant", groq_generate),
}


def _extract_json(text: str) -> str:
    """Strip markdown code fences and preamble text; return the inner JSON object."""
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()

    # Find first JSON object/array in the text, accounting for nested braces
    # and braces inside strings.
    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return text  # No JSON structure found

    open_char = text[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False

    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if not in_string:
            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

    return text[start:]


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


# Kept in sync with server/app/lookup/christian.py. Appended only when the
# pipeline flags possible crisis language: the model picks from all of scripture,
# so the prompt is the only lever for steering away from passages that could harm
# someone in acute distress.
CHRISTIAN_CRISIS_GUARDRAIL = """
This person may be in acute emotional distress or a vulnerable moment. Choose with extra care:
- Strongly prefer verses about God's nearness, comfort, refuge, steadfast love, gentleness, rest, and reassurance (for example "do not be afraid", being carried or held, enduring hope).
- Do NOT select verses about judgment, divine wrath, punishment, condemnation, hell, vengeance, demands to repent, rebuke, correction, or suffering as discipline — even if they seem topically related.
- Never choose a verse that could read as blaming the person or as making God's care conditional on their behavior.
- Keep every shortReason especially gentle and supportive, with no admonition.
"""


def _system_prompt(crisis_flag: bool) -> str:
    """Base selector prompt, plus a safety guardrail when a crisis is flagged."""
    if crisis_flag:
        return CHRISTIAN_SYSTEM_PROMPT + CHRISTIAN_CRISIS_GUARDRAIL
    return CHRISTIAN_SYSTEM_PROMPT


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
            print(f"[christian] Trying provider: {label} ({model})")
            try:
                raw_text, retry_count = await generate_func(
                    _system_prompt(req.crisis_flag), user_prompt
                )
                print(
                    f"[christian] {label} raw response "
                    f"(retry_count={retry_count}): {raw_text[:200]!r}"
                )

                stripped = _extract_json(raw_text)
                if not stripped:
                    raise GeminiError(
                        f"Provider {label} returned empty response. "
                        f"Raw: {raw_text[:200]!r}"
                    )

                try:
                    data = json.loads(stripped)
                except json.JSONDecodeError as e:
                    raise GeminiError(
                        f"Invalid JSON from {label}: {e}\n"
                        f"Stripped: {stripped[:500]!r}\n"
                        f"Original: {raw_text[:500]!r}"
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

                await self._enrich_with_text([primary, *alternates])

                return LookupResult(
                    primary=primary,
                    alternates=alternates,
                    provider=label,
                    model=model,
                    retry_count=retry_count,
                    fallback_used=(name != req.provider),
                )
            except Exception as e:
                print(f"[christian] {label} failed: {type(e).__name__}: {e}")
                last_error = e
                if not _is_retryable(e) or not req.fallback:
                    raise

        raise GeminiError(f"All providers failed. Last error: {last_error}")

    async def _enrich_with_text(self, references: list[Reference]) -> None:
        """Fetch canonical verse text in parallel; mutate references in place.

        Per-ref errors are attached to that Reference and never raised — the
        LLM selection is still useful even if bible-api is rate-limited or down.
        """
        results = await asyncio.gather(
            *(fetch_verse(r.ref) for r in references),
            return_exceptions=True,
        )
        for ref, outcome in zip(references, results):
            if isinstance(outcome, BibleApiError):
                ref.text_error = str(outcome)
                print(f"[christian] verse fetch failed for {ref.ref!r}: {outcome}")
            elif isinstance(outcome, Exception):
                ref.text_error = f"Unexpected: {type(outcome).__name__}: {outcome}"
                print(f"[christian] verse fetch crashed for {ref.ref!r}: {outcome}")
            else:
                ref.text = outcome.text
                ref.translation = outcome.translation_name

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

        if _SCRIPTURE_HINTS.search(short_reason):
            raise GeminiError(
                f"shortReason appears to contain scripture text in {label}: "
                f"{short_reason}"
            )

        return Reference(ref=ref, shortReason=short_reason)
