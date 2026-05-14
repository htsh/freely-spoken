"""Crisis keyword scan on the anonymized text.

Informational only in v1: the flag is returned to the device, which renders
a non-blocking banner. The LLM prompt and response shape do not change when
flagged — coupling product behavior to a naive keyword list would be hard
to test and trivially wrong. Treat this list as a placeholder until v2.
"""

CRISIS_KEYWORDS: tuple[str, ...] = (
    "suicide",
    "self-harm",
    "hurt myself",
    "kill myself",
    "end it all",
)


def check(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)
