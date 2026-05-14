# Lookup Harness

A Mac-local web tool for fast iteration on the verse-selection pipeline — without recording audio on a phone.

## What it does

Picks a sample text (or enter your own), runs it through the same Swift sentiment CLI as the iOS app, then hits your chosen LLM provider for Christian verse selection. Shows the full chain: sentiment → anonymized text → strategy badge → verse references with reasons.

Supports three providers (selectable per-run):
- **Gemini Flash** (gemini-2.0-flash)
- **OpenRouter Free** (openrouter/free)
- **Groq Llama 3.1 8B** (llama-3.1-8b-instant)

Optional fallback chain: if your primary provider returns 429 (rate-limited) or times out, the harness tries the next provider automatically.

## Prerequisites

Same requirements as `tools/sentiment-cli/`:

- macOS 26 (Tahoe) on Apple Silicon (M1+)
- Apple Intelligence enabled in System Settings → Apple Intelligence & Siri
- Swift 6 toolchain (ships with Xcode 26)
- Python 3.11+ (ships with macOS)

## Quick start

```bash
cd tools/lookup-harness
./start.sh
```

Then open <http://localhost:8000>.

## Manual setup (if you prefer)

### 1. Create virtual environment

```bash
cd tools/lookup-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set API keys (optional, for verse lookup)

Add keys for whichever providers you want to use. The harness works with any or none — missing keys just show a clean "lookup error" for the verse step.

```bash
cp .env.example .env
# Edit .env and add your keys:
#   GEMINI_API_KEY     → https://aistudio.google.com/app/apikey
#   OPENROUTER_API_KEY → https://openrouter.ai/keys
#   GROQ_API_KEY       → https://console.groq.com/keys
```

### 3. Start the server

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

## Project layout

```
tools/lookup-harness/
├── app/
│   ├── main.py              # FastAPI entrypoint, routes
│   ├── pipeline.py          # Swift CLI subprocess wrapper + crisis detector
│   ├── providers/
│   │   ├── gemini.py        # Gemini Flash async client
│   │   ├── openrouter.py    # OpenRouter free-tier client
│   │   └── groq.py          # Groq Llama 3.1 8B client
│   ├── lookup/
│   │   ├── base.py          # LookupAdapter Protocol + dataclasses
│   │   ├── christian.py     # Christian verse-pick prompt + parser
│   │   └── stoic.py         # Stub (catalog not yet seeded)
│   └── templates/
│       ├── index.html       # Sample picker, variant toggle, run button
│       └── result.html      # Full pipeline output + verse references
├── fixtures/
│   └── samples.json         # 20 privacy-heavy samples from sentiment-cli
├── pyproject.toml           # Dependencies
├── .env.example             # GEMINI_API_KEY=
└── start.sh                 # One-shot startup script
```

## How it works

```
Browser → POST /run → Swift sentiment-cli --json → sentiment + anonymized text
                                    ↓
                         Provider you selected (dropdown)
                                    ↓
                    [Fallback on 429? → try next provider]
                                    ↓
                              verse references
                                    ↓
                         Render result.html
```

- The Swift subprocess call is real, not mocked — slower (~3–5s) but always current with the CLI prompt.
- The variant toggle is wired end-to-end: Christian calls the selected LLM, Stoic returns a stub.
- Provider + fallback are selectable per-run via the UI dropdown and checkbox.
- Crisis language is flagged (but not blocked) via keyword scan on the anonymized text.

## Troubleshooting

| Problem                                       | Fix                                                                        |
| --------------------------------------------- | -------------------------------------------------------------------------- |
| "Apple Intelligence not available"            | Check macOS 26 + Apple Intelligence enabled in System Settings             |
| `python3: command not found`                  | Install Xcode Command Line Tools: `xcode-select --install`                 |
| `GEMINI_API_KEY environment variable not set`     | Copy `.env.example` to `.env` and add your key                             |
| `OPENROUTER_API_KEY environment variable not set` | Copy `.env.example` to `.env` and add your key                             |
| `GROQ_API_KEY environment variable not set`       | Copy `.env.example` to `.env` and add your key                             |
| Template rendering error                      | Ensure `starlette<1.0` is installed (starlette 1.0 has a Jinja2 cache bug) |
| Port 8000 in use                              | Pass `--port 8001` to uvicorn, or `PORT=8001 ./start.sh`                   |
