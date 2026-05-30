import asyncio
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


CLI_DIR = Path(__file__).parent.parent.parent / "sentiment-cli"

CRISIS_KEYWORDS = [
    "suicide",
    "self-harm",
    "hurt myself",
    "kill myself",
    "end it all",
]


@dataclass
class SentimentResult:
    sentiment: str
    emotions: List[str]
    confidence: float
    anonymizedText: str
    rawStrategy: str
    raw: Optional[str]
    crisisFlag: bool = False


class PipelineError(Exception):
    pass


def _check_crisis(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in CRISIS_KEYWORDS)


def _run_sentiment_sync(text: str) -> SentimentResult:
    try:
        proc = subprocess.run(
            ["swift", "run", "sentiment-cli", "--json", text],
            cwd=CLI_DIR,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise PipelineError("Sentiment CLI timed out after 30 seconds")

    if proc.returncode != 0:
        err_detail = proc.stderr.strip()
        if not err_detail:
            err_detail = f"stdout: {proc.stdout.strip()[:200]}"
        raise PipelineError(
            f"CLI exited with code {proc.returncode}: {err_detail}"
        )

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise PipelineError(
            f"Invalid JSON from CLI: {e}\nStdout: {proc.stdout[:500]}"
        )

    required = ["sentiment", "emotions", "confidence", "anonymizedText", "rawStrategy"]
    missing = [f for f in required if f not in data]
    if missing:
        raise PipelineError(f"Missing fields in CLI output: {missing}")

    crisis = _check_crisis(data["anonymizedText"])

    return SentimentResult(
        sentiment=data["sentiment"],
        emotions=data["emotions"],
        confidence=data["confidence"],
        anonymizedText=data["anonymizedText"],
        rawStrategy=data["rawStrategy"],
        raw=data.get("raw"),
        crisisFlag=crisis,
    )


async def run_sentiment(text: str) -> SentimentResult:
    return await asyncio.to_thread(_run_sentiment_sync, text)
