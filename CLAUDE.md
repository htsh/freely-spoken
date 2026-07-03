# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`README.md` and `AGENTS.md` are the canonical docs. Read `README.md` for the privacy model and architecture, and `AGENTS.md` for working rules. This file is the fast orientation; it does not repeat their detail.

## What this is

**Freely Spoken** (repo `freely-spoken`; the Expo slug remains `mic-check`): an Expo/React Native iOS app plus a FastAPI lookup backend. The user speaks a reflection; the phone transcribes and anonymizes it on-device, then sends only a sanitized summary to the backend, which uses an LLM to *select* a canonical passage (never to author one).

The codebase ships multiple iOS apps from one source via a build-time variant: `christian` (Freely Spoken), `dhammapada` (Idle Ashes, in TestFlight), `stoic` (stub). Variant is chosen by `EXPO_PUBLIC_APP_VARIANT`.

## Commands

App (run from repo root):

```bash
npm run lint        # expo lint
npm run typecheck   # tsc --noEmit (strict)
npm test            # vitest run (pure TS only; no RN/native)
npx vitest run path/to/file.test.ts            # single file
npx vitest run -t "test name"                  # single test by name
npx expo run:ios --device                       # christian build on device
EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo run:ios --device   # Idle Ashes build
```

Backend (run from `server/`):

```bash
pip install -e '.[dev]'
pytest                              # hermetic; providers stubbed, no keys/network
pytest tests/test_dhammapada_catalog.py::test_name
uvicorn app.main:app --reload --port 8080
```

Local iteration tools: `cd tools/lookup-harness && ./start.sh` (prompt/provider web harness at :8000); `cd tools/sentiment-cli && swift run sentiment-cli --raw "..."` (exercise Apple Foundation Models from macOS).

## Hard rules (these are the point of the project)

- **Privacy allowlist.** The only outbound app request is the lookup call, and its body may contain *only* `appVariant`, `anonymizedText`, `sentiment`, `emotions`, `confidence`. Never add audio, raw transcript, file paths, recording duration, device/account/session IDs, or location — not to requests, backend logs, tests, fixtures, or debug output. The allowlist is enforced in `services/lookup-request.ts`; update `services/__tests__/lookup-request.test.ts` whenever that contract changes.
- **Local model output is untrusted.** Apple Foundation Models runs on-device but its output is still parsed/normalized/guarded in `hooks/sentiment-utils.ts` (no RN dependency, so it's unit-testable). Fallback paths must never leak source wording — when anonymization fails the guard, fall back to a generic category sentence, never the raw transcript.
- **LLMs select, they do not author.** The backend LLM picks a Bible reference (Christian, text fetched from a trusted API) or a Dhammapada catalog ID (text loaded from the reviewed `server/app/lookup/dhammapada_catalog.json`). Canonical text never comes from model generation, and passage text is never put in the prompt.
- **Backend logs operational metadata only** — never `anonymizedText` or any user body text.

## Architecture notes

- **Mobile flow** lives in `app/index.tsx`: `idle -> recording -> processing -> review -> responseLookup -> results`. Each pipeline stage is a hook in `hooks/` with the shape `{ result, isLoading, error, action, reset }`. Keep that shape.
- **Layering:** UI primitives in `components/`, screens/flow in `app/`, brand/theme tokens in `constants/`, side-effectful pipeline logic in `hooks/` and `services/`.
- **Backend layering:** `server/app/main.py` is a thin HTTP layer only. Provider fallback chain (Gemini → OpenRouter → Groq, with bounded retry/backoff) lives in `server/app/llm_runner.py`. Per-variant behavior lives in `server/app/lookup/`. When you change a prompt or adapter, check whether `tools/lookup-harness/` needs the same change.
- **Native folders are generated.** `ios/` and `android/` come from Expo prebuild and are git-ignored — do not make durable changes there. Per-variant native identity (display name, bundle IDs, URL schemes, icons, permission strings) lives in `app.config.js`; do not put per-variant identity in `app.json`.
- **Cannot run in Expo Go.** Recording, Apple Speech, and Apple Foundation Models require a native iOS build on Apple-Intelligence-capable hardware.

## Builds & deploy

- EAS profiles in `eas.json` pair each environment with a variant: `*` = christian, `*-idleashes` = dhammapada (which also sets `EXPO_PUBLIC_LOOKUP_API_URL=https://verses.hitesh.nyc`).
- Backend deploy: `server/` defines a Dockerfile and `fly.toml`, but the live host (`verses.hitesh.nyc`) is deployed by rsync + docker build/recreate on a VPS, not git-based. See the backend-deploy memory.
- Device emergency rollback: ship a build with `LOOKUP_API_URL` unset in `app.json` `extra`; the device reverts to the prior flow with no server change.

## Tests to update when behavior changes

- Outbound request shape → `services/__tests__/lookup-request.test.ts`
- Sentiment/anonymization parsing & guards → `hooks/__tests__/use-sentiment-analyzer.test.ts`
- Backend HTTP / crisis / provider / lookup → `server/tests/`
- Dhammapada shortlist/catalog/validation → `server/tests/test_dhammapada_*.py`

Keep backend tests hermetic: stub provider calls rather than requiring keys or network.
