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

    @Guide(description: "Privacy-preserving rewrite that keeps the broad concern and emotional gist while removing identifying specifics.")
    let anonymizedText: String
}

let allowedEmotions = [
    "joy", "sadness", "anger", "fear", "surprise", "disgust",
    "hope", "anxiety", "peace", "love", "gratitude", "frustration",
    "excitement", "confusion",
]

let sentimentPrompt = """
You are a privacy-first sentiment analyzer. Given text, classify its sentiment and emotions.

Return a single JSON object with:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: \(allowedEmotions.joined(separator: ", "))
- confidence: a number between 0 and 1 indicating how confident you are
- anonymizedText: one short de-identified sentence that keeps only the emotional gist and broad concern

If the text is ambiguous, choose the closest sentiment and use a conservative confidence.
For anonymizedText:
- Privacy is more important than specificity. When unsure, generalize or omit the detail.
- Do NOT include any proper nouns or named entities from the input.
- Remove all person names, employer names, school names, clinic names, bank names, organization names, city names, neighborhood names, venue names, dates, times, ages, exact amounts, contact details, account numbers, addresses, medical/legal/financial identifiers, and uniquely identifying events.
- Use broad categories like "the person", "someone close to them", "a workplace", "a healthcare setting", "a legal issue", "a financial concern", or "a recent event".
- Generalize sensitive concepts: medication errors, patient records, pregnancy, diagnosis, relapse, overdose, dementia, visa or immigration details, accusations involving children, drugs, fraud, and retaliation should become broad phrases like "a healthcare issue", "a sensitive personal matter", "a legal concern", or "a workplace power issue".
- Keep only what would help an advice service understand the general situation and emotion.
- Do not add advice, diagnosis, explanations, or facts that are not in the input.
- If a detail could identify a real person, place, organization, or incident, remove it.
Do NOT say "named", "called", "located in", or otherwise preserve an identifying phrase.
Do NOT quote the input.
Do NOT include markdown, code fences, or explanatory text.
"""

// MARK: - CLI plumbing

func readInput(args: [String]) -> (text: String, alsoRunRaw: Bool, jsonOutput: Bool)? {
    var args = args
    var alsoRunRaw = false
    var jsonOutput = false
    if let idx = args.firstIndex(of: "--raw") {
        alsoRunRaw = true
        args.remove(at: idx)
    }
    if let idx = args.firstIndex(of: "--json") {
        jsonOutput = true
        args.remove(at: idx)
    }

    if args.count > 1 {
        return (args.dropFirst().joined(separator: " "), alsoRunRaw, jsonOutput)
    }

    // No argv text — read stdin.
    let data = FileHandle.standardInput.availableData
    if let text = String(data: data, encoding: .utf8)?
        .trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
        return (text, alsoRunRaw, jsonOutput)
    }

    return nil
}

func printErr(_ s: String) {
    FileHandle.standardError.write((s + "\n").data(using: .utf8) ?? Data())
}

// MARK: - Local privacy guard (mirrors the TS-side anonymized text safety layer)

let privacyStopwords: Set<String> = [
    "a", "an", "and", "are", "at", "but", "for", "from", "has", "have", "her",
    "him", "his", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our",
    "she", "so", "that", "the", "their", "them", "they", "this", "to", "was",
    "we", "who", "with",
]

let properNounStopwords: Set<String> = [
    "a", "an", "and", "after", "but", "i", "if", "in", "my", "on", "the",
]

let sensitivePatterns = [
    #"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"#,
    #"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"#,
    #"\b\d+\s+[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl)\b"#,
    #"\$\s?\d[\d,]*(?:\.\d{2})?\b"#,
    #"\b(?:MRN|SSN|account|card|case|claim|policy|passport|license)\s*(?:number|no\.?|#|ending in)?\s*[:#-]?\s*[A-Z0-9-]{3,}\b"#,
    #"\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b"#,
    #"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"#,
    #"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b"#,
    #"\b(?:next|last)\s+(?:week|month|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"#,
    #"\b[A-Z]{2,}\s?\d{2,}\b"#,
    #"\b\d{3,}[-\d]*\b"#,
]

let sensitiveConceptPatterns = [
    #"\bmedication error\b"#,
    #"\bpatient(?:'s)?\s+(?:record|medication|mrn)\b"#,
    #"\bvisa(?:\s+paperwork)?\b"#,
    #"\bimmigration(?:\s+hearing)?\b"#,
    #"\bpregnan(?:t|cy)\b"#,
    #"\bdiagnos(?:is|ed)\b"#,
    #"\brelapse\b"#,
    #"\boverdose(?:d)?\b"#,
    #"\bdementia\b"#,
    #"\baccus(?:e|ed|ation).{0,40}\b(?:child|student)\b"#,
    #"\bhurt(?:ing)?\s+(?:a\s+)?(?:child|student)\b"#,
    #"\bstudent(?:'s)?\s+well-being\b"#,
    #"\bdrugs?\b"#,
    #"\bpills?\b"#,
    #"\bfraud\b"#,
    #"\bretaliat(?:e|es|ed|ing|ion)\b"#,
]

let topicPatterns: [(topic: String, patterns: [String])] = [
    ("workplace", [
        #"\bwork(?:place)?\b"#, #"\bboss\b"#, #"\bmanager\b"#, #"\bdirector\b"#,
        #"\bhr\b"#, #"\bjob\b"#, #"\bfired?\b"#, #"\boffice\b"#, #"\bpayroll\b"#,
        #"\bperformance review\b"#, #"\bvisa paperwork\b"#,
    ]),
    ("healthcare", [
        #"\bclinic\b"#, #"\bhospital\b"#, #"\bsurgery\b"#, #"\bdiagnos(?:is|ed)\b"#,
        #"\bmedication\b"#, #"\bpatient\b"#, #"\btherapist\b"#, #"\brelapse\b"#,
        #"\boverdose\b"#, #"\bdementia\b"#, #"\btreatment\b"#, #"\bpregnant\b"#,
    ]),
    ("legal", [
        #"\bcourt\b"#, #"\bsue\b"#, #"\bhearing\b"#, #"\bpolice\b"#,
        #"\bpulled over\b"#, #"\bimmigration\b"#, #"\blegal\b"#,
    ]),
    ("financial", [
        #"\bmoney\b"#, #"\bborrowed\b"#, #"\bdebt\b"#, #"\bmortgage\b"#,
        #"\baccount\b"#, #"\bcard\b"#, #"\brent\b"#, #"\bpay\b"#, #"\bfraud\b"#,
    ]),
    ("family", [
        #"\bdaughter\b"#, #"\bson\b"#, #"\bhusband\b"#, #"\bwife\b"#,
        #"\bpartner\b"#, #"\bbrother\b"#, #"\bsister\b"#, #"\bmom\b"#,
        #"\bmother\b"#, #"\bfather\b"#, #"\bparent\b"#, #"\bcousin\b"#,
    ]),
    ("housing", [#"\blandlord\b"#, #"\bapartment\b"#, #"\brent\b"#, #"\bhome\b"#]),
    ("school", [#"\bschool\b"#, #"\bteacher\b"#, #"\bprincipal\b"#, #"\bsuspended\b"#]),
    ("safety", [#"\bunsafe\b"#, #"\bthreat(?:en|ened|ening)?\b"#, #"\btrapped\b"#]),
]

let emotionPhrases: [String: String] = [
    "anger": "angry",
    "angry": "angry",
    "anxiety": "anxious",
    "anxious": "anxious",
    "confusion": "confused",
    "confused": "confused",
    "disgust": "upset",
    "excitement": "excited",
    "excited": "excited",
    "fear": "afraid",
    "frustration": "frustrated",
    "frustrated": "frustrated",
    "gratitude": "grateful",
    "guilt": "guilty",
    "helpless": "helpless",
    "hope": "hopeful",
    "joy": "joyful",
    "love": "loving",
    "panic": "anxious",
    "peace": "calm",
    "relief": "relieved",
    "sadness": "sad",
    "surprise": "surprised",
]

func regexMatches(_ text: String, pattern: String) -> Bool {
    guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
        return false
    }
    return regex.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) != nil
}

func regexMatches(_ text: String, pattern: String, options: NSRegularExpression.Options) -> [String] {
    guard let regex = try? NSRegularExpression(pattern: pattern, options: options) else {
        return []
    }

    let matches = regex.matches(in: text, range: NSRange(text.startIndex..., in: text))
    return matches.compactMap { match in
        guard let range = Range(match.range, in: text) else {
            return nil
        }
        return String(text[range])
    }
}

func significantTokens(_ text: String) -> Set<String> {
    let tokens = text
        .lowercased()
        .components(separatedBy: CharacterSet.alphanumerics.inverted)
        .filter { $0.count >= 4 && !privacyStopwords.contains($0) }

    return Set(tokens)
}

func inferPrivateTopic(sourceText: String) -> String {
    var topics: [String] = []

    for topicPattern in topicPatterns {
        if topicPattern.patterns.contains(where: { regexMatches(sourceText, pattern: $0) }) {
            topics.append(topicPattern.topic)
        }
    }

    let uniqueTopics = Array(NSOrderedSet(array: topics).compactMap { $0 as? String }).prefix(2)
    return uniqueTopics.isEmpty ? "personal" : uniqueTopics.joined(separator: " and ")
}

func describeEmotions(_ emotions: [String]) -> String {
    let phrases = emotions.compactMap { emotionPhrases[$0.lowercased()] }

    if phrases.isEmpty {
        return "concerned"
    }

    if phrases.count == 1 {
        return phrases[0]
    }

    return "\(phrases[0]) and \(phrases[1])"
}

func buildAnonymizedFallback(sourceText: String, emotions: [String]) -> String {
    "The person is dealing with a private \(inferPrivateTopic(sourceText: sourceText)) situation and feels \(describeEmotions(emotions))."
}

func extractProtectedTerms(sourceText: String) -> [String] {
    let matches = regexMatches(
        sourceText,
        pattern: #"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"#,
        options: []
    )

    var seen = Set<String>()
    return matches.compactMap { match in
        let normalized = match.lowercased()
        guard match.count >= 3, !properNounStopwords.contains(normalized), !seen.contains(normalized) else {
            return nil
        }
        seen.insert(normalized)
        return match
    }
}

func containsProtectedTerm(_ candidate: String, sourceText: String) -> Bool {
    extractProtectedTerms(sourceText: sourceText).contains { term in
        let pattern = "\\b\(NSRegularExpression.escapedPattern(for: term))\\b"
        return regexMatches(candidate, pattern: pattern)
    }
}

func containsSensitivePattern(_ candidate: String) -> Bool {
    sensitivePatterns.contains { regexMatches(candidate, pattern: $0) }
}

func containsSensitiveConcept(_ candidate: String) -> Bool {
    sensitiveConceptPatterns.contains { regexMatches(candidate, pattern: $0) }
}

func isTooSimilarToSource(_ candidate: String, sourceText: String) -> Bool {
    let candidateTokens = significantTokens(candidate)
    if candidateTokens.count < 5 {
        return false
    }

    let sourceTokens = significantTokens(sourceText)
    let overlap = candidateTokens.filter { sourceTokens.contains($0) }.count
    return Double(overlap) / Double(candidateTokens.count) >= 0.65
}

func guardAnonymizedText(_ value: String?, sourceText: String, emotions: [String]) -> String {
    guard let value else {
        return buildAnonymizedFallback(sourceText: sourceText, emotions: emotions)
    }

    let trimmed = value
        .components(separatedBy: .whitespacesAndNewlines)
        .filter { !$0.isEmpty }
        .joined(separator: " ")

    if trimmed.isEmpty {
        return buildAnonymizedFallback(sourceText: sourceText, emotions: emotions)
    }

    if containsProtectedTerm(trimmed, sourceText: sourceText)
        || containsSensitivePattern(trimmed)
        || containsSensitiveConcept(trimmed)
        || isTooSimilarToSource(trimmed, sourceText: sourceText) {
        return buildAnonymizedFallback(sourceText: sourceText, emotions: emotions)
    }

    return trimmed
}

func extractFirstJSONObject(_ text: String) -> String? {
    let chars = Array(text)
    var start: Int?
    var depth = 0
    var inString = false
    var isEscaped = false

    for (index, char) in chars.enumerated() {
        if start == nil {
            if char == "{" {
                start = index
                depth = 1
            }
            continue
        }

        if inString {
            if isEscaped {
                isEscaped = false
                continue
            }

            if char == "\\" {
                isEscaped = true
                continue
            }

            if char == "\"" {
                inString = false
            }

            continue
        }

        if char == "\"" {
            inString = true
            continue
        }

        if char == "{" {
            depth += 1
            continue
        }

        if char == "}" {
            depth -= 1
            if depth == 0, let start {
                return String(chars[start...index])
            }
        }
    }

    return nil
}

// MARK: - JSON output (for --json flag)

struct JSONOutput: Codable {
    let sentiment: String
    let emotions: [String]
    let confidence: Double
    let anonymizedText: String
    let rawStrategy: String
    let raw: String?
}

// MARK: - Main (top-level — main.swift cannot also use @main)

guard let input = readInput(args: CommandLine.arguments) else {
    printErr("usage: sentiment-cli [--raw] [--json] <text>   (or pipe text on stdin)")
    exit(2)
}

// Availability check matches the TS hook's getTextModelAvailability gate.
let model = SystemLanguageModel.default
guard model.availability == .available else {
    printErr("Apple Intelligence is not available: \(model.availability)")
    exit(1)
}

let session = LanguageModelSession(instructions: sentimentPrompt)

if input.jsonOutput {
    // JSON mode: try structured first, fallback to text generation.
    do {
        let response = try await session.respond(to: input.text, generating: Sentiment.self)
        let guarded = guardAnonymizedText(
            response.content.anonymizedText,
            sourceText: input.text,
            emotions: response.content.emotions
        )
        let output = JSONOutput(
            sentiment: response.content.sentiment,
            emotions: response.content.emotions,
            confidence: response.content.confidence,
            anonymizedText: guarded,
            rawStrategy: "generateObject",
            raw: nil
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        let data = try encoder.encode(output)
        print(String(data: data, encoding: .utf8)!)
    } catch {
        // Fallback to text generation
        do {
            let textSession = LanguageModelSession(instructions: sentimentPrompt)
            let raw = try await textSession.respond(to: input.text)
            if let rawJSON = extractFirstJSONObject(raw.content),
               let data = rawJSON.data(using: .utf8),
               let parsed = try? JSONDecoder().decode(Sentiment.self, from: data) {
                let guarded = guardAnonymizedText(
                    parsed.anonymizedText,
                    sourceText: input.text,
                    emotions: parsed.emotions
                )
                let output = JSONOutput(
                    sentiment: parsed.sentiment,
                    emotions: parsed.emotions,
                    confidence: parsed.confidence,
                    anonymizedText: guarded,
                    rawStrategy: "generateText-fallback",
                    raw: raw.content
                )
                let encoder = JSONEncoder()
                encoder.outputFormatting = [.sortedKeys]
                let data = try encoder.encode(output)
                print(String(data: data, encoding: .utf8)!)
            } else {
                let output = JSONOutput(
                    sentiment: "",
                    emotions: [],
                    confidence: 0,
                    anonymizedText: "",
                    rawStrategy: "generateText-fallback",
                    raw: raw.content
                )
                let encoder = JSONEncoder()
                encoder.outputFormatting = [.sortedKeys]
                let data = try encoder.encode(output)
                print(String(data: data, encoding: .utf8)!)
            }
        } catch {
            let output = JSONOutput(
                sentiment: "",
                emotions: [],
                confidence: 0,
                anonymizedText: "",
                rawStrategy: "failed",
                raw: nil
            )
            let encoder = JSONEncoder()
            encoder.outputFormatting = [.sortedKeys]
            let data = try encoder.encode(output)
            print(String(data: data, encoding: .utf8)!)
            exit(1)
        }
    }
} else {
    // Human-readable mode (original behavior).

    // Structured (generateObject equivalent).
    do {
        let response = try await session.respond(to: input.text, generating: Sentiment.self)
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(response.content)
        print("--- structured (Generable) ---")
        print(String(data: data, encoding: .utf8) ?? "<encoding error>")
        print("\n--- guarded structured anonymizedText ---")
        print(guardAnonymizedText(
            response.content.anonymizedText,
            sourceText: input.text,
            emotions: response.content.emotions
        ))
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

            if let rawJSON = extractFirstJSONObject(raw.content),
               let data = rawJSON.data(using: .utf8),
               let parsed = try? JSONDecoder().decode(Sentiment.self, from: data) {
                print("\n--- guarded raw anonymizedText ---")
                print(guardAnonymizedText(
                    parsed.anonymizedText,
                    sourceText: input.text,
                    emotions: parsed.emotions
                ))
            }
        } catch {
            printErr("raw generation failed: \(error)")
        }
    }
}
