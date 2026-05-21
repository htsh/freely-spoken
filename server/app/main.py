"""FastAPI entrypoint for the mic-check lookup service.

Endpoints:
- POST /lookup  — the device contract; see schemas.LookupRequestBody / LookupResult.
- GET  /healthz — uptime probe.

The HTTP layer is intentionally thin: validate body, enforce client secret,
dispatch by appVariant to the registered adapter, map adapter errors onto
structured `{ error: { code, message } }` responses. Provider fallback,
retries, and Bible API fetch all live below in adapter / runner code.
"""

import asyncio
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # noqa: E402 — must run before importing modules that read env

from fastapi import FastAPI, Header, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from app.config import SETTINGS  # noqa: E402
from app.crisis import check as check_crisis  # noqa: E402
from app.llm_runner import AllProvidersFailedError  # noqa: E402
from app.lookup.base import LookupRequest  # noqa: E402
from app.lookup.bible_api import BibleApiError  # noqa: E402
from app.lookup.christian import ChristianAdapter, ChristianAdapterError  # noqa: E402
from app.lookup.stoic import StoicAdapter  # noqa: E402
from app.schemas import (  # noqa: E402
    ErrorBody,
    ErrorResponse,
    LookupRequestBody,
    LookupResult,
    ReferenceModel,
    StoicStubResult,
)


logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}',
    stream=sys.stdout,
)
logger = logging.getLogger("lookup")


ADAPTERS = {
    "christian": ChristianAdapter(),
    "stoic": StoicAdapter(),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.semaphore = asyncio.Semaphore(SETTINGS.max_concurrency)
    yield


app = FastAPI(title="mic-check-lookup", lifespan=lifespan)


def _error_response(
    status: int, code: str, message: str, *, request_id: str | None = None
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message))
    if request_id:
        return JSONResponse(
            status_code=status,
            content=body.model_dump(),
            headers={"X-Lookup-Request-ID": request_id},
        )
    return JSONResponse(status_code=status, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError):
    # Pydantic's full validation report leaks the request shape into 400s,
    # which is fine for a private API. We pick the first error message for
    # the human-readable field and surface the rest in logs.
    first = exc.errors()[0] if exc.errors() else {"msg": "invalid request"}
    return _error_response(400, "invalid_request", str(first.get("msg", "invalid request")))


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/lookup")
async def lookup(
    body: LookupRequestBody,
    request: Request,
    x_lookup_client_secret: str | None = Header(default=None, alias="X-Lookup-Client-Secret"),
    x_client_request_id: str | None = Header(default=None, alias="X-Client-Request-ID"),
) -> JSONResponse:
    request_id = str(uuid.uuid4())
    started = time.monotonic()

    if SETTINGS.client_secret is not None and x_lookup_client_secret != SETTINGS.client_secret:
        return _error_response(
            401,
            "unauthorized",
            "missing or invalid client secret",
            request_id=request_id,
        )

    adapter = ADAPTERS.get(body.appVariant)
    if adapter is None:
        return _error_response(
            400,
            "unknown_variant",
            f"unknown appVariant: {body.appVariant}",
            request_id=request_id,
        )

    crisis_flag = check_crisis(body.anonymizedText)

    if body.appVariant == "stoic":
        # Stoic stub bypasses LLM + Bible API entirely.
        stub = await adapter.select(LookupRequest(  # type: ignore[arg-type]
            anonymized_text=body.anonymizedText,
            sentiment=body.sentiment,
            emotions=body.emotions,
            confidence=body.confidence,
        ))
        _log_request(
            request_id=request_id,
            client_request_id=x_client_request_id,
            variant=body.appVariant,
            body=body,
            outcome="stoic_stub",
            crisis_flag=crisis_flag,
            started=started,
            provider="none",
            model="none",
            retry_count=0,
            fallback_used=False,
        )
        payload = StoicStubResult(**stub, crisisFlag=crisis_flag).model_dump()
        return JSONResponse(
            status_code=200,
            content=payload,
            headers={"X-Lookup-Request-ID": request_id},
        )

    sem: asyncio.Semaphore = request.app.state.semaphore

    try:
        async with sem:
            result = await adapter.select(LookupRequest(
                anonymized_text=body.anonymizedText,
                sentiment=body.sentiment,
                emotions=body.emotions,
                confidence=body.confidence,
            ))
    except AllProvidersFailedError as e:
        _log_request(
            request_id=request_id,
            client_request_id=x_client_request_id,
            variant=body.appVariant,
            body=body,
            outcome="all_providers_failed",
            crisis_flag=crisis_flag,
            started=started,
            error=repr(e.last_error),
        )
        return _error_response(
            502,
            "all_providers_failed",
            str(e),
            request_id=request_id,
        )
    except ChristianAdapterError as e:
        _log_request(
            request_id=request_id,
            client_request_id=x_client_request_id,
            variant=body.appVariant,
            body=body,
            outcome="adapter_malformed",
            crisis_flag=crisis_flag,
            started=started,
            error=str(e),
        )
        return _error_response(
            502,
            "all_providers_failed",
            str(e),
            request_id=request_id,
        )
    except BibleApiError as e:
        # _enrich_with_text swallows individual failures into textError, so a
        # raw BibleApiError reaching here means a non-fetch path failed.
        _log_request(
            request_id=request_id,
            client_request_id=x_client_request_id,
            variant=body.appVariant,
            body=body,
            outcome="bible_api_down",
            crisis_flag=crisis_flag,
            started=started,
            error=str(e),
        )
        return _error_response(
            502,
            "bible_api_down",
            str(e),
            request_id=request_id,
        )
    except Exception as e:  # last-resort
        logger.exception(
            '"unexpected_error", "request_id": "%s", "client_request_id": "%s", "variant": "%s"',
            request_id,
            x_client_request_id,
            body.appVariant,
        )
        return _error_response(
            500,
            "internal_error",
            f"{type(e).__name__}",
            request_id=request_id,
        )

    refs = [result.primary, *result.alternates]
    if refs and all(r.textError and not r.text for r in refs):
        _log_request(
            request_id=request_id,
            client_request_id=x_client_request_id,
            variant=body.appVariant,
            body=body,
            outcome="bible_api_down",
            crisis_flag=crisis_flag,
            started=started,
            provider=result.provider,
            model=result.model,
            retry_count=result.retry_count,
            fallback_used=result.fallback_used,
        )
        return _error_response(
            502,
            "bible_api_down",
            "every reference fetch failed",
            request_id=request_id,
        )

    _log_request(
        request_id=request_id,
        client_request_id=x_client_request_id,
        variant=body.appVariant,
        body=body,
        outcome="ok",
        crisis_flag=crisis_flag,
        started=started,
        provider=result.provider,
        model=result.model,
        retry_count=result.retry_count,
        fallback_used=result.fallback_used,
    )

    payload = LookupResult(
        primary=ReferenceModel(**result.primary.__dict__),
        alternates=[ReferenceModel(**r.__dict__) for r in result.alternates],
        provider=result.provider,
        model=result.model,
        retryCount=result.retry_count,
        fallbackUsed=result.fallback_used,
        crisisFlag=crisis_flag,
    )
    return JSONResponse(
        status_code=200,
        content=payload.model_dump(),
        headers={"X-Lookup-Request-ID": request_id},
    )


def _log_request(
    *,
    request_id: str,
    client_request_id: str | None,
    variant: str,
    body: LookupRequestBody,
    outcome: str,
    crisis_flag: bool,
    started: float,
    provider: str = "",
    model: str = "",
    retry_count: int = 0,
    fallback_used: bool = False,
    error: str | None = None,
) -> None:
    # Logged: enough to debug latency, fallback behavior, and outcome.
    # NOT logged: anonymizedText body — only its length and the sentiment label
    # metadata. Even anonymized text would be upsetting if leaked from logs.
    latency_ms = round((time.monotonic() - started) * 1000)
    payload = {
        "request_id": request_id,
        "client_request_id": client_request_id or "",
        "variant": variant,
        "sentiment": body.sentiment,
        "emotions": body.emotions,
        "confidence": body.confidence,
        "anonymized_text_len": len(body.anonymizedText),
        "outcome": outcome,
        "crisis_flag": crisis_flag,
        "latency_ms": latency_ms,
        "provider": provider,
        "model": model,
        "retry_count": retry_count,
        "fallback_used": fallback_used,
    }
    if error:
        payload["error"] = error
    import json
    logger.info(json.dumps(payload))
