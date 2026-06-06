# HuggingFace backstop cost smoke test

A standalone probe for the **paid last-resort provider** (`huggingface`, the end
of the lookup chain). It fires N real requests, reads the *actual* token usage
from each response, and tells you what the calls cost. Use it to confirm the
backstop is cheap enough that you're safe to ship to TestFlight / the App Store.

Only the rare **all-providers-failed** tail ever reaches this provider, so in
practice it bills almost nothing — this script lets you put a real number on
"almost nothing."

## Requirements

- Python 3.9+
- `httpx` (`pip install httpx`)
- `HF_TOKEN` in the environment (the same token in the backend `.env`)

No app code — it's self-contained, so it runs anywhere you can reach the
internet.

## Run it

```bash
export HF_TOKEN=hf_...           # your HuggingFace token
python hf_cost_smoke.py 20       # 20 requests
python hf_cost_smoke.py 30 --concurrency 2
```

Override the model or pricing:

```bash
python hf_cost_smoke.py 20 \
  --model openai/gpt-oss-20b:fireworks-ai \
  --in-price 0.10 --out-price 0.50        # $ per 1M tokens
```

### ⚠️ Set the real prices

The default `--in-price` / `--out-price` are **estimates**. The token *counts*
are measured for real, but the dollar figure is only as good as the rates you
give it. Look up the current price for your model on the HuggingFace router
(Inference Providers) / the upstream provider (here Fireworks) and pass the real
numbers. The script prints the rates it used so you can't miss them.

## Reading the output

- **OK / Failed** — success rate. Any failure prints its reason (bad token,
  rate limit, model id typo...).
- **Latency** — min / p50 / p95 / max / mean in ms.
- **Tokens** — total and per-call input/output.
- **Cost** — total for the run, per call, and extrapolations (1k / 10k calls,
  and how long the $300 credit lasts at that rate).

## Copy it to vps1 (next to the load test)

```bash
scp hf_cost_smoke.py vps1:~/loadtest/
# then on vps1:
ssh vps1
cd ~/loadtest && export HF_TOKEN=hf_... && python hf_cost_smoke.py 30
```

## Note vs. `server/scripts/hf_smoke.py`

That one is a **single-call health check** (is the backstop alive?) that imports
the app adapter. This one is a **standalone cost/load probe** (what would N calls
cost?) with no app dependency, meant to be copied around.
