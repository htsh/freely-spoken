// sentiment-cli — runs the same sentiment-analysis prompt against Apple's on-device
// Foundation Models LLM so we can iterate on prompts and inspect raw output without
// rebuilding the React Native app or running on a phone.
//
// Usage:
//   swift run sentiment-cli "I'm feeling pretty good today, all things considered."
//   echo "transcript here" | swift run sentiment-cli
//   swift run sentiment-cli --raw "transcript"   # also print unstructured generateText output
//
// Requires macOS 26+ on Apple Silicon with Apple Intelligence enabled in System Settings.
//
// IMPORTANT: keep `sentimentPrompt` and the `Sentiment` schema in sync with
// hooks/use-sentiment-analyzer.ts in the parent project. They are intentionally
// duplicated rather than shared so this tool stays a single-file Swift package.

import Foundation
import FoundationModels

// MARK: - Schema (mirrors SENTIMENT_SCHEMA in use-sentiment-analyzer.ts)

@Generable
struct Sentiment: Codable {
    @Guide(description: "Exactly one of: positive, negative, neutral")
    let sentiment: String

    @Guide(description: "Emotions present in the text. Choose only from the allowed list.")
    let emotions: [String]

    @Guide(description: "Confidence between 0 and 1.")
    let confidence: Double
}

let allowedEmotions = [
    "joy", "sadness", "anger", "fear", "surprise", "disgust",
    "hope", "anxiety", "peace", "love", "gratitude", "frustration",
    "excitement", "confusion",
]

let sentimentPrompt = """
You are a sentiment analyzer. Given text, classify its sentiment and emotions.

Return a single JSON object with:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: \(allowedEmotions.joined(separator: ", "))
- confidence: a number between 0 and 1 indicating how confident you are

If the text is ambiguous, choose the closest sentiment and use a conservative confidence.
Do NOT repeat or paraphrase any of the input text.
Do NOT include markdown, code fences, or explanatory text.
"""

// MARK: - CLI plumbing

func readInput(args: [String]) -> (text: String, alsoRunRaw: Bool)? {
    var args = args
    var alsoRunRaw = false
    if let idx = args.firstIndex(of: "--raw") {
        alsoRunRaw = true
        args.remove(at: idx)
    }

    if args.count > 1 {
        return (args.dropFirst().joined(separator: " "), alsoRunRaw)
    }

    // No argv text — read stdin.
    let data = FileHandle.standardInput.availableData
    if let text = String(data: data, encoding: .utf8)?
        .trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
        return (text, alsoRunRaw)
    }

    return nil
}

func printErr(_ s: String) {
    FileHandle.standardError.write((s + "\n").data(using: .utf8) ?? Data())
}

// MARK: - Main (top-level — main.swift cannot also use @main)

guard let input = readInput(args: CommandLine.arguments) else {
    printErr("usage: sentiment-cli [--raw] <text>   (or pipe text on stdin)")
    exit(2)
}

// Availability check matches the TS hook's getTextModelAvailability gate.
let model = SystemLanguageModel.default
guard model.availability == .available else {
    printErr("Apple Intelligence is not available: \(model.availability)")
    exit(1)
}

let session = LanguageModelSession(instructions: sentimentPrompt)

// Structured (generateObject equivalent).
do {
    let response = try await session.respond(to: input.text, generating: Sentiment.self)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    let data = try encoder.encode(response.content)
    print("--- structured (Generable) ---")
    print(String(data: data, encoding: .utf8) ?? "<encoding error>")
} catch {
    printErr("structured generation failed: \(error)")
}

// Optional unstructured pass — useful to see what the model would have returned
// without schema constraints (this is what triggers the TS hook's text-fallback path).
if input.alsoRunRaw {
    do {
        let textSession = LanguageModelSession(instructions: sentimentPrompt)
        let raw = try await textSession.respond(to: input.text)
        print("\n--- raw (generateText) ---")
        print(raw.content)
    } catch {
        printErr("raw generation failed: \(error)")
    }
}
