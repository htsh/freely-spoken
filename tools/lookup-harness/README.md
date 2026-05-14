# Lookup Harness

A Mac-local web tool for fast iteration on the verse-selection pipeline — without recording audio on a phone.

## What it does

Picks a sample text (or enter your own), runs it through the same Swift sentiment CLI as the iOS app, then hits Gemini Flash for Christian verse selection. Shows the full chain: sentiment → anonymized text → strategy badge → verse references with reasons.

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

### 2. Set Gemini API key (optional, for verse lookup)

```bash
cp .env.example .env
# Edit .env and add your key from https://aistudio.google.com/app/apikey
```

Without a key, the harness still runs sentiment + anonymization and shows a clean "lookup error" for the verse step.

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
│   │   └── gemini.py        # Gemini Flash async client
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
                         Gemini Flash (if GEMINI_API_KEY set)
                                    ↓
                              verse references
                                    ↓
                         Render result.html
```

- The Swift subprocess call is real, not mocked — slower (~3–5s) but always current with the CLI prompt.
- The variant toggle is wired end-to-end: Christian calls Gemini, Stoic returns a stub.
- Crisis language is flagged (but not blocked) via keyword scan on the anonymized text.

## Troubleshooting

| Problem                                       | Fix                                                                        |
| --------------------------------------------- | -------------------------------------------------------------------------- |
| "Apple Intelligence not available"            | Check macOS 26 + Apple Intelligence enabled in System Settings             |
| `python3: command not found`                  | Install Xcode Command Line Tools: `xcode-select --install`                 |
| `GEMINI_API_KEY environment variable not set` | Copy `.env.example` to `.env` and add your key                             |
| Template rendering error                      | Ensure `starlette<1.0` is installed (starlette 1.0 has a Jinja2 cache bug) |
| Port 8000 in use                              | Pass `--port 8001` to uvicorn, or `PORT=8001 ./start.sh`                   |
