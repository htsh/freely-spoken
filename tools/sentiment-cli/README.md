# sentiment-cli

A tiny Swift command-line tool that runs the same sentiment-analysis prompt as `hooks/use-sentiment-analyzer.ts` against Apple's on-device Foundation Models LLM. Lets you iterate on prompts and inspect raw model output without rebuilding the React Native app or running on a phone.

## Requirements

- macOS 26 (Tahoe) on Apple Silicon (M1+)
- Apple Intelligence enabled in System Settings → Apple Intelligence & Siri
- Swift 6 toolchain (ships with Xcode 26)

## Usage

From `tools/sentiment-cli/`:

```bash
# Inline argument
swift run sentiment-cli "I'm feeling pretty good today, all things considered."

# stdin
echo "I keep waking up at 3am with my chest tight." | swift run sentiment-cli

# Also print the unstructured generateText output (the TS fallback path)
swift run sentiment-cli --raw "Whatever. The meeting happened. It was fine."

# Sweep a JSONL file of {"text": "..."} fixtures
jq -r '.text' fixtures.jsonl | while IFS= read -r line; do
  echo "=== $line ==="
  echo "$line" | swift run sentiment-cli
done
```

First run will build; subsequent runs are fast. Pass `-c release` for a faster build if you're sweeping a lot of inputs.

## Keeping in sync with the app

The `sentimentPrompt` string and the `Sentiment` `@Generable` struct in `Sources/sentiment-cli/main.swift` are intentional duplicates of `SENTIMENT_PROMPT` and `SENTIMENT_SCHEMA` in `hooks/use-sentiment-analyzer.ts`. If you change one, change the other. The TS side has additional normalization (alias maps, brace-matched JSON extraction) that this tool deliberately does **not** replicate — the point of the CLI is to see what the model actually emits before that layer cleans it up.
