"""Christian variant adapter.

LLM picks a primary Bible reference + 2 alternates with short reasons. The
adapter never trusts the LLM for scripture text — every reference is fetched
from the configured Bible API before responding. Individual fetch failures
become per-Reference textError fields; the response is still useful with
references and reasons alone.
"""

import asyncio
import json
import re

from app.lookup.base import LookupRequest, LookupResult, Reference
from app.lookup.bible_api import BibleApiError, fetch_verse
from app.llm_runner import AllProvidersFailedError, OutputValidationError, run as run_llm

REF_PATTERN = re.compile(r"^[1-3]?\s?[A-Za-z]+\s\d+:\d+(-\d+)?$")
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
# Catches obvious cases where the model dumps a long scripture-style quotation
# into shortReason. Not foolproof — three sentences is the harder cap.
_SCRIPTURE_HINTS = re.compile(
    r'"[^"]{120,}"|saith the LORD|verily I say|thus says the Lord',
    re.IGNORECASE,
)


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


# Appended to the system prompt only when the HTTP layer flags possible crisis
# language (see app.crisis.check). The Dhammapada adapter can shrink a candidate
# catalog the model never sees; the Christian adapter lets the model pick from
# all of scripture, so the prompt is the only lever for steering away from
# passages that could harm someone in acute distress. This is a tone/selection
# constraint — it discloses no user content to the model.
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


class ChristianAdapterError(OutputValidationError):
    """Raised when LLM output is malformed enough to be unusable.

    Subclasses OutputValidationError so the runner treats it as a provider
    failure and falls through to the next provider instead of failing outright.
    """


def _extract_json(text: str) -> str:
    text = text.strip()
    match = _JSON_FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()

    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return text

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


def _make_reference(data: dict, label: str) -> Reference:
    if "ref" not in data or "shortReason" not in data:
        raise ChristianAdapterError(
            f"Missing ref or shortReason in {label}: {data}"
        )

    ref = data["ref"]
    if not REF_PATTERN.match(ref):
        raise ChristianAdapterError(f"Invalid ref format in {label}: {ref}")

    short_reason = data["shortReason"]
    sentences = [s.strip() for s in short_reason.split(".") if s.strip()]
    if len(sentences) < 1 or len(sentences) > 3:
        raise ChristianAdapterError(
            f"shortReason must be 1-3 sentences in {label}: {short_reason}"
        )

    if _SCRIPTURE_HINTS.search(short_reason):
        raise ChristianAdapterError(
            f"shortReason appears to contain scripture text in {label}: "
            f"{short_reason}"
        )

    return Reference(ref=ref, shortReason=short_reason)


async def _enrich_with_text(references: list[Reference]) -> None:
    """Fetch canonical text in parallel; mutate references in place.

    Per-ref errors are attached to that Reference and never raised. The
    caller checks whether *all* fetches failed and downgrades to bible_api_down.
    """
    results = await asyncio.gather(
        *(fetch_verse(r.ref) for r in references),
        return_exceptions=True,
    )
    for ref, outcome in zip(references, results):
        if isinstance(outcome, BibleApiError):
            ref.textError = str(outcome)
        elif isinstance(outcome, Exception):
            ref.textError = f"Unexpected: {type(outcome).__name__}: {outcome}"
        else:
            ref.text = outcome.text
            ref.translation = outcome.translation_name


def _user_prompt(req: LookupRequest) -> str:
    return (
        f"Anonymized text: {req.anonymized_text}\n"
        f"Sentiment: {req.sentiment}\n"
        f"Emotions: {', '.join(req.emotions)}\n"
        f"Confidence: {req.confidence}"
    )


class ChristianAdapter:
    app_variant = "christian"

    async def select(self, req: LookupRequest) -> LookupResult:
        def _parse(text: str) -> tuple[Reference, list[Reference]]:
            """Validate one provider's output; raise to fall through to the next."""
            stripped = _extract_json(text)
            if not stripped:
                raise ChristianAdapterError(
                    f"LLM returned empty/unparseable response. Raw: {text[:200]!r}"
                )

            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as e:
                raise ChristianAdapterError(
                    f"Invalid JSON: {e}\nStripped: {stripped[:500]!r}"
                ) from e

            if "primary" not in data or "alternates" not in data:
                raise ChristianAdapterError(
                    f"Missing primary or alternates in response: {data}"
                )

            alternates_data = data["alternates"]
            if not isinstance(alternates_data, list) or len(alternates_data) != 2:
                raise ChristianAdapterError(
                    f"Expected exactly 2 alternates, got: {alternates_data}"
                )

            primary = _make_reference(data["primary"], "primary")
            alternates = [
                _make_reference(a, f"alternate[{i}]")
                for i, a in enumerate(alternates_data)
            ]
            return primary, alternates

        llm = await run_llm(
            _system_prompt(req.crisis_flag), _user_prompt(req), validate=_parse
        )
        primary, alternates = llm.parsed

        await _enrich_with_text([primary, *alternates])

        return LookupResult(
            primary=primary,
            alternates=alternates,
            provider=llm.provider,
            model=llm.model,
            retry_count=llm.retry_count,
            fallback_used=llm.fallback_used,
            providers_attempted=llm.providers_attempted,
            provider_errors=llm.provider_errors,
        )


# Re-export error types the HTTP layer needs to catch for clean error mapping.
__all__ = [
    "ChristianAdapter",
    "ChristianAdapterError",
    "AllProvidersFailedError",
]
