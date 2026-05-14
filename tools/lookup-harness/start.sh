#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
VENV_DIR=".venv"

# ── Python check ─────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
	echo "Error: python3 not found. Install Xcode Command Line Tools:"
	echo "  xcode-select --install"
	exit 1
fi

# ── Virtual environment ──────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtual environment..."
	python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# ── Dependencies ───────────────────────────────────────────────
if [ ! -f "$VENV_DIR/.installed" ] || [ requirements.txt -nt "$VENV_DIR/.installed" ]; then
	echo "Installing dependencies..."
	pip install -q -r requirements.txt
	touch "$VENV_DIR/.installed"
fi

# ── .env check ─────────────────────────────────────────────────
if [ ! -f .env ]; then
	echo ""
	echo "Tip: copy .env.example to .env and add GEMINI_API_KEY for verse lookup."
	echo "     Without a key, sentiment + anonymization still works."
	echo ""
fi

# ── Start ──────────────────────────────────────────────────────
echo "Starting harness on http://localhost:$PORT"
echo "  Sample picker: http://localhost:$PORT/"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
