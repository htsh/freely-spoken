# Home GPU Overflow Plan — Free Chain Primary, 3060 Backup, 3090 Ti Burst

**Status:** Draft. Not yet wired. Use after free-tier chain proves insufficient in production.

## Architecture decision

**Free API chain is primary.** Home GPU is last-resort overflow only. This preserves the $0-cost beta launch and only pays electricity when the free chain burns out.

Current free chain: `gemini → openrouter → groq → cloudflare → together → cerebras` = **~17,500–22,500 requests/day**.

Hardware ready:
- **Backup**: Ryzen 5 1600 AF + RTX 3060 12GB (always-on, ~$12–20/month)
- **Burst**: RTX 3090 Ti 24GB (WOL, manual or scheduled wake)

## Why this exists

## 3060: Software setup

### Model choice

The 3060 has **12GB VRAM**. Llama 3.1 8B FP16 is **~16GB** — won’t fit.

| Quantization | Size | Quality | Fit |
|---|---|---|---|
| Q4_K_M (INT4) | ~5GB | Good | Comfortable |
| Q8_0 (INT8) | ~8.5GB | Excellent | Tight but works |
| FP16 | ~16GB | Best | ❌ Won’t fit |

**Recommendation**: Start with **Q8_0** for verse-selection quality. Drop to Q4_K_M if VRAM pressure causes OOM under load.

### Option A: llama.cpp (simpler)

```bash
# Download quantized model
wget https://huggingface.co/QuantFactory/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct.Q8_0.gguf

# Start OpenAI-compatible server
./server -m Meta-Llama-3.1-8B-Instruct.Q8_0.gguf \
  -c 4096 \
  --port 8000 \
  --host 0.0.0.0
```

Pros: single binary, easy to restart, battle-tested.
Cons: slightly slower than vLLM, no batching optimization.

### Option B: vLLM (faster, production-grade)

```bash
# Requires ~8.5GB VRAM for INT8 AWQ
python -m vllm.entrypoints.openai.api_server \
  --model casperhansen/llama-3.1-8b-instruct-awq \
  --quantization awq \
  --max-model-len 4096 \
  --port 8000 \
  --host 0.0.0.0
```

Pros: batching, continuous batching, higher throughput (~3–8 req/s on 3060).
Cons: more dependencies, larger install.

**Start with llama.cpp.** Migrate to vLLM if you need >5 concurrent users or want to squeeze more throughput from the hardware.

### Autostart on boot

Create `~/.config/systemd/user/llama-server.service`:

```ini
[Unit]
Description=Llama.cpp OpenAI-compatible server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/user/llama
ExecStart=/home/user/llama/server \
  -m /home/user/models/llama-3.1-8b-instruct.Q8_0.gguf \
  -c 4096 --port 8000 --host 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable llama-server.service
systemctl --user start llama-server.service
```

## Exposing to the internet

The Fly.io backend needs to reach your home server. Options:

### Option A: Cloudflare Tunnel (recommended)

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate (one-time)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create mic-check-gpu

# Route to local llama.cpp
cloudflared tunnel route dns mic-check-gpu llama.mydomain.com

# Start tunnel
cloudflared tunnel run mic-check-gpu --url http://localhost:8000
```

Pros: HTTPS out of the box, no dynamic IP pain, free.
Cons: adds ~20–50ms latency, Cloudflare dependency.

### Option B: Tailscale

If the Fly.io backend (or a lightweight sidecar) can join the same Tailnet:

```bash
tailscale up --advertise-exit-node
```

Backend connects directly to `http://home-server:8000` over encrypted WireGuard.

Pros: no public exposure, lower latency.
Cons: requires Tailscale on both sides.

### Option C: Dynamic DNS + Port Forward

Only if your ISP gives you a real public IP. Expose port 8000, firewall to Fly.io egress IPs.

## Backend provider module

Add `server/app/providers/homegpu.py`:

```python
import os
import httpx

HOME_GPU_URL = os.getenv("HOME_GPU_URL", "https://llama.mydomain.com/v1/chat/completions")
HOME_GPU_MODEL = "llama-3.1-8b-instruct"

NAME = "homegpu"
MODEL = HOME_GPU_MODEL


class HomeGpuError(Exception):
    pass


async def generate(system_prompt: str, user_prompt: str) -> str:
    api_key = os.getenv("HOME_GPU_API_KEY")  # optional, if you add auth
    async with httpx.AsyncClient(timeout=10) as client:  # shorter timeout — local
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            response = await client.post(
                HOME_GPU_URL,
                headers=headers,
                json={
                    "model": HOME_GPU_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HomeGpuError(f"Home GPU error {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise HomeGpuError(f"Home GPU unreachable: {e}") from e

    data = response.json()
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise HomeGpuError(f"Unexpected home GPU response: {data}") from e

    if not text or not text.strip():
        raise HomeGpuError("Home GPU returned empty content")

    return text
```

Wire into `llm_runner.py`:
1. Import `homegpu`
2. Add to `PROVIDERS` dict
3. Add `HomeGpuError` to `_ERRORS`
4. Set `LOOKUP_PROVIDER_ORDER=homegpu,gemini,openrouter,groq,cloudflare,together,cerebras` to make home GPU primary

Or leave it last for overflow-only:
`LOOKUP_PROVIDER_ORDER=gemini,openrouter,groq,cloudflare,together,cerebras,homegpu`

## Health check before routing

Add a lightweight health check to avoid routing to a cold or crashed server:

```python
# In llm_runner.py, before trying homegpu
async def _homegpu_healthy() -> bool:
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            r = await client.get(HOME_GPU_URL.replace("/chat/completions", "/health"))
            return r.status_code == 200
    except Exception:
        return False
```

llama.cpp has a `/health` endpoint when started with `--server`. vLLM has `/health` by default.

## 3090 Ti: Burst capacity

### When to wake it

- Scheduled: `rtcwake` at 6 PM, sleep at midnight (peak usage window)
- Manual: Alert fires when `AllProvidersFailedError` rate spikes
- On-demand: You WOL it from your phone when testing

### Setup

```bash
# Check if WOL is enabled on NIC
sudo ethtool eth0 | grep Wake-on

# If not: enable persistent WOL
sudo ethtool -s eth0 wol g
sudo systemctl enable wol@eth0
```

### WOL script

```bash
#!/bin/bash
# wake-3090ti.sh — run from any machine on the LAN
MAC="xx:xx:xx:xx:xx:xx"
wakeonlan $MAC
```

### Model loading on the 3090 Ti

With 24GB VRAM, you can run **FP16** (full quality, no quantization):

```bash
./server -m Meta-Llama-3.1-8B-Instruct-f16.gguf \
  -c 4096 --port 8001 --host 0.0.0.0
```

Or **Q8_0** if you want to run multiple model copies or larger context.

**Latency on 3090 Ti**: ~50–150ms per lookup (vs. ~200–600ms on 3060).

### Switching backends

Option 1: **Two tunnels** — `llama-3060.mydomain.com` and `llama-3090ti.mydomain.com`. Backend tries 3060 first, falls back to 3090 Ti.

Option 2: **Single backend, manual swap** — when 3090 Ti wakes, stop 3060 tunnel, start 3090 Ti tunnel at the same URL. Zero backend code changes.

## Monitoring

### What to track

- GPU utilization: `nvidia-smi dmon -s u` — should spike during inference, idle near 0%
- VRAM usage: `nvidia-smi` — Q8_0 uses ~8.5GB, should not OOM
- Request latency: log in backend, alert if p95 > 2s (indicates 3060 is struggling)
- Tunnel uptime: Cloudflare dashboard or `cloudflared tunnel info`
- Electricity: smart plug with power monitoring (TP-Link Kasa, etc.) — validate actual wall draw

### Alert thresholds

- `AllProvidersFailedError` > 5% in 5 minutes → wake 3090 Ti or check home server
- 3060 GPU temp > 85°C → thermal throttling, check case airflow
- Tunnel down > 2 minutes → ISP issue, fallback to free APIs

## Cost comparison

| Setup | Monthly cost | Capacity | Latency | Maintenance |
|---|---|---|---|---|
| Free API chain only | $0 | ~22K/day | 1–30s (spiky) | 6 API keys |
| **3060 always-on** | **~$12–20** | **unlimited** | **~200–600ms** | **reboots, updates** |
| 3090 Ti always-on | ~$18–28 | unlimited | ~50–150ms | reboots, updates |
| Groq paid | ~$10 | ~66K/month | ~50ms | 1 API key |
| Fly.io GPU (A100) | $300–500 | unlimited | ~50ms | managed |

## Decision tree

```
Free chain handling load?
├── Yes → Keep free chain, monitor
└── No (burning out daily, high error rate)
    ├── 3060 already on for other uses? → Wire as primary or fallback
    ├── 3060 would be dedicated? → Compare vs Groq paid (~$10/mo)
    │   ├── Want zero API dependency? → 3060
    │   └── Want zero maintenance? → Groq paid
    └── Need <150ms latency or >10 concurrent users? → Wake 3090 Ti
```

## Migration checklist (when ready)

1. [ ] Pick quantization (Q8_0 or Q4_K_M) and download GGUF
2. [ ] Install llama.cpp or vLLM on 1600AF + 3060
3. [ ] Start server, verify `/health` responds
4. [ ] Test a few verse-selection prompts locally: `curl http://localhost:8000/v1/chat/completions`
5. [ ] Set up Cloudflare tunnel or Tailscale
6. [ ] Add `HOME_GPU_URL` env var to Fly.io backend
7. [ ] Create `server/app/providers/homegpu.py` and wire into `llm_runner.py`
8. [ ] Set `LOOKUP_PROVIDER_ORDER` — decide primary vs. fallback position
9. [ ] Deploy backend, send test request from app, verify `provider: "homegpu"` in response
10. [ ] Set up `nvidia-smi` monitoring or smart plug logging
11. [ ] Configure WOL for 3090 Ti (optional burst)
12. [ ] Document actual wall power draw after 1 week of real usage
