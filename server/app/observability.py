"""Optional Sentry reporting for rare operational failures.

Wired so the backend runs identically with or without Sentry: if SENTRY_DSN is
unset (or sentry-sdk isn't installed), every function here is a no-op. The only
event we report is the black-swan "all providers failed" — at real concurrency
this never fires, so it is a genuine signal rather than noise.

Privacy: this module never receives or sends user body text. It is handed only
provider metadata (names + failure reasons), and Sentry is initialized with PII
off and a before_send hook that strips any request body as defense in depth.
"""

import logging
import os

logger = logging.getLogger(__name__)

try:
    import sentry_sdk
except ImportError:  # sentry-sdk is an optional dependency
    sentry_sdk = None

_initialized = False


def _scrub_body(event: dict, hint: dict) -> dict:
    """Defense in depth: never let a request body or cookies reach Sentry."""
    req = event.get("request")
    if isinstance(req, dict):
        req.pop("data", None)
        req.pop("cookies", None)
    return event


def init_sentry() -> bool:
    """Initialize Sentry if configured. Returns True if it was enabled."""
    global _initialized
    dsn = os.getenv("SENTRY_DSN")
    if not dsn or sentry_sdk is None:
        logger.info("sentry_disabled", extra={"reason": "no_dsn" if not dsn else "not_installed"})
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        send_default_pii=False,
        traces_sample_rate=0.0,
        before_send=_scrub_body,
    )
    _initialized = True
    logger.info("sentry_enabled")
    return True


def report_all_providers_failed(*, request_id: str, variant: str, error) -> None:
    """Report an exhausted provider chain with operational context only."""
    if not _initialized or sentry_sdk is None:
        return
    with sentry_sdk.new_scope() as scope:
        scope.set_tag("variant", variant)
        scope.set_tag("lookup_request_id", request_id)
        scope.set_context(
            "provider_chain",
            {
                "attempted": getattr(error, "providers_attempted", []),
                "errors": getattr(error, "provider_errors", {}),
                "last_error": repr(getattr(error, "last_error", None)),
            },
        )
        sentry_sdk.capture_message("all_providers_failed", level="error")
