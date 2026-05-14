from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import json

from fastapi import FastAPI, Form, Request
from fastapi.templating import Jinja2Templates

from app.pipeline import PipelineError, run_sentiment
from app.lookup.base import LookupRequest
from app.lookup.christian import ChristianAdapter
from app.lookup.stoic import StoicAdapter
from app.providers.gemini import GeminiError

ADAPTERS = {
    "christian": ChristianAdapter(),
    "stoic": StoicAdapter(),
}

app = FastAPI()
templates = Jinja2Templates(directory=[str(Path(__file__).parent / "templates")])

SAMPLES_PATH = Path(__file__).parent.parent / "fixtures" / "samples.json"


def load_samples():
    with open(SAMPLES_PATH) as f:
        return json.load(f)


@app.get("/")
async def index(request: Request):
    samples = load_samples()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "samples": samples}
    )


@app.post("/run")
async def run(
    request: Request,
    sample_id: str = Form(""),
    text: str = Form(""),
    variant: str = Form("christian"),
):
    samples = load_samples()
    sample_map = {s["id"]: s["text"] for s in samples}

    if sample_id and sample_id in sample_map:
        input_text = sample_map[sample_id]
    else:
        input_text = text

    error = None
    result = None
    try:
        result = await run_sentiment(input_text)
    except PipelineError as e:
        error = str(e)
    except Exception as e:
        error = f"Unexpected error: {e}"

    lookup_result = None
    lookup_error = None
    if not error and result:
        adapter = ADAPTERS.get(variant)
        if adapter:
            lookup_req = LookupRequest(
                anonymized_text=result.anonymizedText,
                sentiment=result.sentiment,
                emotions=result.emotions,
                confidence=str(result.confidence),
            )
            try:
                lookup_result = await adapter.select(lookup_req)
            except GeminiError as e:
                lookup_error = str(e)
            except Exception as e:
                lookup_error = f"Unexpected lookup error: {e}"

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "input_text": input_text,
            "result": result,
            "variant": variant,
            "error": error,
            "lookup_result": lookup_result,
            "lookup_error": lookup_error,
        }
    )
