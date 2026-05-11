# sentiment-cli

A tiny Swift command-line tool that runs the same sentiment + anonymization prompt as `hooks/use-sentiment-analyzer.ts` against Apple's on-device Foundation Models LLM. Lets you iterate on prompts and inspect raw model output without rebuilding the React Native app or running on a phone.

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

# Includes anonymizedText in the structured output
swift run sentiment-cli "My name is Maya Patel and the surgery at Northstar Clinic in Denver left me scared."

# Also print the unstructured generateText output (the TS fallback path)
swift run sentiment-cli --raw "Whatever. The meeting happened. It was fine."

# Run 20 privacy-heavy samples and eyeball raw vs guarded output
./run-anonymization-samples.sh

# Sweep a JSONL file of {"text": "..."} fixtures
jq -r '.text' fixtures.jsonl | while IFS= read -r line; do
  echo "=== $line ==="
  echo "$line" | swift run sentiment-cli
done
```

First run will build; subsequent runs are fast. Pass `-c release` for a faster build if you're sweeping a lot of inputs.

The CLI prints model output first, then `guarded ... anonymizedText`. The guarded line applies the local privacy safety layer that the React Native hook uses before showing or sending anonymized text.

## Keeping in sync with the app

The `sentimentPrompt` string, the `Sentiment` `@Generable` struct, and the anonymized-text guard in `Sources/sentiment-cli/main.swift` intentionally mirror `hooks/use-sentiment-analyzer.ts`. If you change one, change the other. The CLI still shows raw model output so you can see what the model emitted before the guard cleaned it up.
