#!/usr/bin/env python3
"""Batch labeling driver for the Dhammapada catalog (tasks 3.1, 3.2).

Development-only data-prep tool. Reads the seed catalog, runs the two-pass
labeling prompts (prompts/semantic-pass.md, prompts/safety-tone-pass.md)
through a chosen provider/model, parses + validates each pass against the
frozen vocabulary, merges both passes onto the seed row, and stamps per-row
provenance (labeledBy, labeledAt, promptVersion).

Pure stdlib HTTP (urllib) so it runs with no pip install. Most candidate
providers (Fireworks, HF router, Groq, OpenRouter, Together, Cerebras) expose
an OpenAI-compatible /chat/completions endpoint and share one client; pick the
preset with --provider. Replicate is not OpenAI-compatible — stubbed for now.

Examples:
    # offline plumbing test — no API key, deterministic mock provider
    python label_catalog.py --provider mock --limit 5 --out outputs/mock.json

    # provider/model evaluation over the curated eval sample (task 3.4)
    python label_catalog.py --provider fireworks \\
        --model accounts/fireworks/models/llama-v3p1-70b-instruct \\
        --sample eval_sample.json --out outputs/eval.fireworks-70b.json

    # full corpus run (after a model is chosen, task 2.6)
    python label_catalog.py --provider fireworks --model <id> \\
        --out outputs/catalog.labeled.json

Outputs a labeled catalog JSON plus a sibling <out>.report.json run report
(provider, model, counts, JSON-validity rate, vocab-failure rate, latency,
token estimate) to support the provider comparison in task 3.5.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import validate as V  # noqa: E402  (sibling module: vocab loader + row validator)

# ── Provider presets ───────────────────────────────────────────────────
# All OpenAI-compatible /chat/completions. base_url is the API root; the
# client appends /chat/completions. api_key_env names the env var to read.
PRESETS = {
    "fireworks":  {"base_url": "https://api.fireworks.ai/inference/v1",
                   "api_key_env": "FIREWORKS_API_KEY"},
    "hf-router":  {"base_url": "https://router.huggingface.co/v1",
                   "api_key_env": "HF_TOKEN"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1",
                   "api_key_env": "GROQ_API_KEY"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1",
                   "api_key_env": "OPENROUTER_API_KEY"},
    "together":   {"base_url": "https://api.together.xyz/v1",
                   "api_key_env": "TOGETHER_API_KEY"},
    "cerebras":   {"base_url": "https://api.cerebras.ai/v1",
                   "api_key_env": "CEREBRAS_API_KEY"},
    "mock":       {"base_url": None, "api_key_env": None},
    "replicate":  {"base_url": None, "api_key_env": "REPLICATE_API_TOKEN"},
}


@dataclass
class LabelConfig:
    provider: str
    model: str = ""
    prompt_version: str = "labeling-v1.0"
    limit: int = 0                 # 0 = no limit
    sample_path: str = ""          # JSON list of ids to label (eval subset)
    max_retries: int = 3
    backoff_base: float = 2.0      # seconds; jittered exponential
    timeout: int = 60
    temperature: float = 0.2
    out_path: str = "outputs/catalog.labeled.json"
    vocab_path: str = V.DEFAULT_VOCAB
    seed_path: str = os.path.join(HERE, "catalog.seed.json")


class ProviderError(Exception):
    pass


# ── HTTP provider (OpenAI-compatible) ──────────────────────────────────
class OpenAICompatProvider:
    def __init__(self, cfg: LabelConfig):
        preset = PRESETS[cfg.provider]
        self.base_url = preset["base_url"]
        self.model = cfg.model
        self.temperature = cfg.temperature
        self.timeout = cfg.timeout
        key_env = preset["api_key_env"]
        self.api_key = os.getenv(key_env) if key_env else None
        if not self.api_key:
            raise ProviderError(
                f"{cfg.provider}: env var {key_env} is not set")
        if not self.model:
            raise ProviderError(f"{cfg.provider}: --model is required")

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Authorization": f"Bearer {self.api_key}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            payload = json.load(resp)
        text = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        return text, usage


class MockProvider:
    """Deterministic, schema-valid stand-in for offline plumbing tests."""
    def __init__(self, cfg: LabelConfig):
        self.model = cfg.model or "mock-1"

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        pid = re.search(r"Passage id:\s*(\S+)", user).group(1)
        if "semantic" in system.lower() or "what the passage is about" in system.lower():
            obj = {"id": pid, "themes": ["mind"], "summary": "Mock paraphrase.",
                   "emotionalFit": ["peace"], "useWhen": ["rumination"]}
        else:
            obj = {"id": pid, "tone": "direct", "avoidWhen": [],
                   "vulnerableStatesToAvoid": [], "riskNotes": ""}
        return json.dumps(obj), {"prompt_tokens": 0, "completion_tokens": 0}


class ReplicateProvider:
    def __init__(self, cfg: LabelConfig):
        raise ProviderError(
            "replicate provider not implemented: Replicate uses an async "
            "create-prediction + poll API, not OpenAI-compatible chat. Add a "
            "client here if a Replicate-hosted model wins the eval. For now "
            "evaluate Replicate models via their OpenAI-compatible endpoints "
            "where available, or use fireworks/hf-router.")


def make_provider(cfg: LabelConfig):
    if cfg.provider == "mock":
        return MockProvider(cfg)
    if cfg.provider == "replicate":
        return ReplicateProvider(cfg)
    if cfg.provider not in PRESETS:
        raise ProviderError(f"unknown provider '{cfg.provider}'; "
                            f"known: {', '.join(PRESETS)}")
    return OpenAICompatProvider(cfg)


# ── Prompt rendering ────────────────────────────────────────────────────
def load_prompt(path: str) -> tuple[str, str]:
    """Parse a prompt file into (system_template, user_template)."""
    raw = open(path, encoding="utf-8").read()
    # sections delimited by '## SYSTEM' and '## USER'; header comments ignored
    m = re.search(r"##\s*SYSTEM\s*\n(.*?)\n##\s*USER\s*\n(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"{path}: missing ## SYSTEM / ## USER sections")
    return m.group(1).strip(), m.group(2).strip()


def render_vocab(system: str, vocab: dict) -> str:
    return (system
            .replace("{{VOCAB_THEMES}}", ", ".join(vocab["themes"]))
            .replace("{{VOCAB_USEWHEN}}", ", ".join(vocab["useWhen"]))
            .replace("{{VOCAB_EMOTIONALFIT}}", ", ".join(vocab["emotionalFit"]))
            .replace("{{VOCAB_TONE}}", ", ".join(vocab["tone"]))
            .replace("{{VOCAB_AVOIDWHEN}}", ", ".join(vocab["avoidWhen"])))


def render_user(user_tmpl: str, row: dict) -> str:
    return (user_tmpl
            .replace("{{PASSAGE_ID}}", row["id"])
            .replace("{{PASSAGE_REF}}", row["passageRef"])
            .replace("{{PASSAGE_CHAPTER}}", row["chapter"])
            .replace("{{PASSAGE_TEXT}}", row["text"]))


# ── JSON extraction (tolerant of prose around the object) ───────────────
def extract_json(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in model output")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    raise ValueError("unbalanced JSON object in model output")


# ── Retry wrapper ───────────────────────────────────────────────────────
def call_with_retry(provider, system, user, cfg: LabelConfig):
    last = None
    for attempt in range(cfg.max_retries + 1):
        try:
            t0 = time.time()
            text, usage = provider.complete(system, user)
            return text, usage, time.time() - t0
        except (urllib.error.HTTPError, urllib.error.URLError, ProviderError) as e:
            last = e
            code = getattr(e, "code", None)
            # 4xx other than 429 won't fix on retry
            if code is not None and 400 <= code < 500 and code != 429:
                break
            if attempt < cfg.max_retries:
                import random
                time.sleep(cfg.backoff_base * (2 ** attempt) * (0.5 + random.random()))
    raise ProviderError(f"call failed after retries: {last}")


# ── Single-pass validation against vocab (pre-merge) ────────────────────
def check_pass(obj: dict, pass_name: str, expect_id: str, vocab: dict) -> list[str]:
    errs = []
    if obj.get("id") != expect_id:
        errs.append(f"id mismatch: got {obj.get('id')!r}, expected {expect_id!r}")
    if pass_name == "semantic":
        for f, key in (("themes", "themes"), ("useWhen", "useWhen"),
                       ("emotionalFit", "emotionalFit")):
            bad = [v for v in (obj.get(f) or []) if v not in set(vocab[key])]
            if bad:
                errs.append(f"{f} out-of-vocab: {bad}")
        if not (obj.get("summary") or "").strip():
            errs.append("empty summary")
    else:
        if obj.get("tone") not in set(vocab["tone"]):
            errs.append(f"tone out-of-vocab: {obj.get('tone')!r}")
        bad = [v for v in (obj.get("avoidWhen") or []) if v not in set(vocab["avoidWhen"])]
        if bad:
            errs.append(f"avoidWhen out-of-vocab: {bad}")
        vsa = set(obj.get("vulnerableStatesToAvoid") or [])
        if not vsa <= set(obj.get("avoidWhen") or []):
            errs.append("vulnerableStatesToAvoid not subset of avoidWhen")
    return errs


SEMANTIC_FIELDS = ("themes", "summary", "emotionalFit", "useWhen")
SAFETY_FIELDS = ("tone", "avoidWhen", "vulnerableStatesToAvoid", "riskNotes")


def label_row(row, provider, prompts, vocab, cfg, report):
    """Run both passes for one row; return (merged_row_or_None, ok)."""
    rid = row["id"]
    merged = dict(row)
    for pass_name, (system_t, user_t) in prompts.items():
        system = render_vocab(system_t, vocab)
        user = render_user(user_t, row)
        try:
            text, usage, dt = call_with_retry(provider, system, user, cfg)
        except ProviderError as e:
            report["errors"].append(f"{rid}/{pass_name}: {e}")
            return None, False
        report["latencies"].append(dt)
        report["prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
        report["completion_tokens"] += usage.get("completion_tokens", 0) or 0
        report["calls"] += 1
        try:
            obj = extract_json(text)
        except ValueError as e:
            report["json_failures"] += 1
            report["errors"].append(f"{rid}/{pass_name}: bad JSON ({e})")
            return None, False
        verrs = check_pass(obj, pass_name, rid, vocab)
        if verrs:
            report["vocab_failures"] += 1
            report["errors"].append(f"{rid}/{pass_name}: " + "; ".join(verrs))
            return None, False
        fields = SEMANTIC_FIELDS if pass_name == "semantic" else SAFETY_FIELDS
        for f in fields:
            merged[f] = obj.get(f, merged.get(f))
    # stamp provenance
    merged["labeledBy"] = f"{cfg.provider}/{provider.model}"
    merged["labeledAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    merged["promptVersion"] = cfg.prompt_version
    merged["excludeOnCrisis"] = False
    merged["reviewedBy"] = None
    return merged, True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=list(PRESETS))
    ap.add_argument("--model", default="")
    ap.add_argument("--prompt-version", default="labeling-v1.0")
    ap.add_argument("--limit", type=int, default=0, help="label only first N rows")
    ap.add_argument("--sample", default="", help="JSON file: list of ids to label")
    ap.add_argument("--max-retries", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--out", default="outputs/catalog.labeled.json")
    ap.add_argument("--vocab", default=V.DEFAULT_VOCAB)
    args = ap.parse_args(argv)

    cfg = LabelConfig(
        provider=args.provider, model=args.model, prompt_version=args.prompt_version,
        limit=args.limit, sample_path=args.sample, max_retries=args.max_retries,
        temperature=args.temperature, out_path=args.out, vocab_path=args.vocab)

    vocab = V.load_vocab(cfg.vocab_path)
    seed = json.load(open(cfg.seed_path, encoding="utf-8"))
    rows = seed["rows"]

    if cfg.sample_path:
        data = json.load(open(cfg.sample_path, encoding="utf-8"))
        wanted = set(data["ids"] if isinstance(data, dict) else data)
        rows = [r for r in rows if r["id"] in wanted]
    if cfg.limit:
        rows = rows[:cfg.limit]

    prompts = {
        "semantic": load_prompt(os.path.join(HERE, "prompts", "semantic-pass.md")),
        "safety": load_prompt(os.path.join(HERE, "prompts", "safety-tone-pass.md")),
    }

    provider = make_provider(cfg)
    report = {"provider": cfg.provider, "model": cfg.model or getattr(provider, "model", ""),
              "promptVersion": cfg.prompt_version, "rowsAttempted": len(rows),
              "rowsLabeled": 0, "calls": 0, "json_failures": 0, "vocab_failures": 0,
              "prompt_tokens": 0, "completion_tokens": 0, "latencies": [], "errors": []}

    labeled = []
    for i, row in enumerate(rows, 1):
        merged, ok = label_row(row, provider, prompts, vocab, cfg, report)
        if ok:
            labeled.append(merged)
            report["rowsLabeled"] += 1
        print(f"[{i}/{len(rows)}] {row['id']} {'ok' if ok else 'FAIL'}",
              file=sys.stderr)

    out = {"labeledAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
           "provider": cfg.provider, "model": report["model"],
           "promptVersion": cfg.prompt_version, "grouping": seed.get("grouping"),
           "rowCount": len(labeled), "rows": labeled}
    os.makedirs(os.path.dirname(cfg.out_path) or ".", exist_ok=True)
    json.dump(out, open(cfg.out_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    lat = report["latencies"]
    summary = {k: report[k] for k in ("provider", "model", "promptVersion",
               "rowsAttempted", "rowsLabeled", "calls", "json_failures",
               "vocab_failures", "prompt_tokens", "completion_tokens")}
    summary["avg_latency_s"] = round(sum(lat) / len(lat), 2) if lat else None
    summary["json_valid_rate"] = round(
        1 - report["json_failures"] / report["calls"], 3) if report["calls"] else None
    summary["errors"] = report["errors"]
    json.dump(summary, open(cfg.out_path + ".report.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\nlabeled {report['rowsLabeled']}/{report['rowsAttempted']} rows "
          f"-> {cfg.out_path}", file=sys.stderr)
    print(f"json failures: {report['json_failures']}, vocab failures: "
          f"{report['vocab_failures']}, avg latency: {summary['avg_latency_s']}s",
          file=sys.stderr)
    return 0 if report["rowsLabeled"] == report["rowsAttempted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
