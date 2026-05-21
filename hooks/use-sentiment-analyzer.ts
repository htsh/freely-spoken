import { useState, useCallback } from 'react';
import {
  generateObject,
  generateText,
  getTextModelAvailability,
} from '@ratley/react-native-apple-foundation-models';
import type { JSONSchema } from '@ratley/react-native-apple-foundation-models';

const SENTIMENTS = ['positive', 'negative', 'neutral'] as const;

const EMOTIONS = [
  'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
  'hope', 'anxiety', 'peace', 'love', 'gratitude', 'frustration',
  'excitement', 'confusion',
] as const;

type Sentiment = (typeof SENTIMENTS)[number];
type Emotion = (typeof EMOTIONS)[number];

type RawSentimentResult = {
  sentiment?: unknown;
  emotions?: unknown;
  confidence?: unknown;
  anonymizedText?: unknown;
};

class SentimentFallbackParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SentimentFallbackParseError';
  }
}

const SENTIMENT_SCHEMA = {
  type: 'object',
  required: ['sentiment', 'emotions', 'confidence', 'anonymizedText'],
  properties: {
    sentiment: {
      type: 'string',
      minLength: 1,
    },
    emotions: {
      type: 'array',
      items: { type: 'string' },
    },
    confidence: {
      type: 'number',
      minimum: 0,
      maximum: 100,
    },
    anonymizedText: {
      type: 'string',
      minLength: 1,
    },
  },
} satisfies JSONSchema;

export type SentimentResult = {
  sentiment: Sentiment;
  emotions: Emotion[];
  confidence: number;
  anonymizedText: string;
};

export type RawSentimentResponse = {
  /** Which path produced this output. `text-fallback` means generateObject failed and we re-asked with generateText. */
  strategy: 'object' | 'text-fallback';
  /** Pretty-printed model output (object stringified, or raw text for the fallback path). */
  value: string;
};

const SENTIMENT_PROMPT = `You are a privacy-first sentiment analyzer. Given text, classify its sentiment and emotions.

Return a single JSON object with:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: ${EMOTIONS.join(', ')}
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
Do NOT include markdown, code fences, or explanatory text.`;

const SENTIMENT_ALIASES: Record<string, Sentiment> = {
  positive: 'positive',
  negative: 'negative',
  neutral: 'neutral',
  mixed: 'neutral',
};

const EMOTION_ALIASES: Record<string, Emotion> = {
  anger: 'anger',
  angry: 'anger',
  anxiety: 'anxiety',
  anxious: 'anxiety',
  calm: 'peace',
  calmness: 'peace',
  confusion: 'confusion',
  confused: 'confusion',
  disgust: 'disgust',
  disgusted: 'disgust',
  excitement: 'excitement',
  excited: 'excitement',
  fear: 'fear',
  frustrated: 'frustration',
  frustration: 'frustration',
  grateful: 'gratitude',
  gratitude: 'gratitude',
  happy: 'joy',
  hopeful: 'hope',
  hope: 'hope',
  joy: 'joy',
  joyful: 'joy',
  love: 'love',
  loving: 'love',
  peace: 'peace',
  peaceful: 'peace',
  sadness: 'sadness',
  sad: 'sadness',
  scared: 'fear',
  surprise: 'surprise',
  surprised: 'surprise',
  thankful: 'gratitude',
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function logSentimentDebug(event: string, details?: Record<string, unknown>): void {
  if (!__DEV__) {
    return;
  }
  if (details) {
    console.log('[sentiment]', event, details);
    return;
  }
  console.log('[sentiment]', event);
}

function summarizeFallbackParse(text: string): Record<string, unknown> {
  const extracted = extractFirstJSONObject(text);
  const candidate = extracted ?? text;
  const trimmed = text.trim();
  const candidateTrimmed = candidate.trim();

  return {
    responseLength: text.length,
    trimmedResponseLength: trimmed.length,
    startsWithCodeFence: trimmed.startsWith('```'),
    extractedJSONObject: extracted !== null,
    candidateLength: candidate.length,
    candidateFirstChar: candidateTrimmed.length > 0 ? candidateTrimmed.charAt(0) : null,
    containsOpenBrace: text.includes('{'),
    containsCloseBrace: text.includes('}'),
  };
}

function normalizeLabel(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z\s-]/g, '').replace(/\s+/g, ' ');
}

function normalizeSentiment(value: unknown): Sentiment {
  if (typeof value !== 'string') {
    return 'neutral';
  }

  const normalized = normalizeLabel(value);

  if (SENTIMENT_ALIASES[normalized]) {
    return SENTIMENT_ALIASES[normalized];
  }

  if (normalized.includes('positive')) {
    return 'positive';
  }

  if (normalized.includes('negative')) {
    return 'negative';
  }

  return 'neutral';
}

function normalizeEmotion(value: string): Emotion | null {
  const normalized = normalizeLabel(value);
  if (!normalized) {
    return null;
  }

  if (EMOTIONS.includes(normalized as Emotion)) {
    return normalized as Emotion;
  }

  if (EMOTION_ALIASES[normalized]) {
    return EMOTION_ALIASES[normalized];
  }

  for (const [alias, emotion] of Object.entries(EMOTION_ALIASES)) {
    if (normalized.includes(alias)) {
      return emotion;
    }
  }

  return null;
}

function normalizeEmotions(value: unknown): Emotion[] {
  const rawValues = Array.isArray(value)
    ? value
    : typeof value === 'string'
      ? [value]
      : [];

  const normalized = rawValues.flatMap((item) => {
    if (typeof item !== 'string') {
      return [];
    }

    return item
      .split(/,|\/|\band\b/gi)
      .map((part) => normalizeEmotion(part))
      .filter((emotion): emotion is Emotion => emotion !== null);
  });

  return [...new Set(normalized)];
}

function normalizeConfidence(value: unknown): number {
  let parsed: number | null = null;

  if (typeof value === 'number' && Number.isFinite(value)) {
    parsed = value;
  } else if (typeof value === 'string') {
    const stripped = value.trim().replace('%', '');
    const numeric = Number.parseFloat(stripped);
    if (Number.isFinite(numeric)) {
      parsed = numeric;
    }
  }

  if (parsed === null) {
    return 0.5;
  }

  const normalized = parsed > 1 ? parsed / 100 : parsed;
  return Math.min(Math.max(normalized, 0), 1);
}

const PRIVACY_STOPWORDS = new Set([
  'a', 'an', 'and', 'are', 'at', 'but', 'for', 'from', 'has', 'have', 'her',
  'him', 'his', 'i', 'in', 'is', 'it', 'me', 'my', 'of', 'on', 'or', 'our',
  'she', 'so', 'that', 'the', 'their', 'them', 'they', 'this', 'to', 'was',
  'we', 'who', 'with',
]);

const PROPER_NOUN_STOPWORDS = new Set([
  'a', 'an', 'and', 'after', 'but', 'i', 'if', 'in', 'my', 'on', 'the',
]);

const SENSITIVE_PATTERNS = [
  /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i,
  /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/,
  /\b\d+\s+[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Way|Place|Pl)\b/i,
  /\$\s?\d[\d,]*(?:\.\d{2})?\b/,
  /\b(?:MRN|SSN|account|card|case|claim|policy|passport|license)\s*(?:number|no\.?|#|ending in)?\s*[:#-]?\s*[A-Z0-9-]{3,}\b/i,
  /\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b/i,
  /\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i,
  /\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\b/i,
  /\b(?:next|last)\s+(?:week|month|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/i,
  /\b[A-Z]{2,}\s?\d{2,}\b/,
  /\b\d{3,}[-\d]*\b/,
];

const SENSITIVE_CONCEPT_PATTERNS = [
  /\bmedication error\b/i,
  /\bpatient(?:'s)?\s+(?:record|medication|mrn)\b/i,
  /\bvisa(?:\s+paperwork)?\b/i,
  /\bimmigration(?:\s+hearing)?\b/i,
  /\bpregnan(?:t|cy)\b/i,
  /\bdiagnos(?:is|ed)\b/i,
  /\brelapse\b/i,
  /\boverdose(?:d)?\b/i,
  /\bdementia\b/i,
  /\baccus(?:e|ed|ation).{0,40}\b(?:child|student)\b/i,
  /\bhurt(?:ing)?\s+(?:a\s+)?(?:child|student)\b/i,
  /\bstudent(?:'s)?\s+well-being\b/i,
  /\bdrugs?\b/i,
  /\bpills?\b/i,
  /\bfraud\b/i,
  /\bretaliat(?:e|es|ed|ing|ion)\b/i,
];

const TOPIC_PATTERNS: Array<{ topic: string; patterns: RegExp[] }> = [
  {
    topic: 'workplace',
    patterns: [
      /\bwork(?:place)?\b/i, /\bboss\b/i, /\bmanager\b/i, /\bdirector\b/i,
      /\bhr\b/i, /\bjob\b/i, /\bfired?\b/i, /\boffice\b/i, /\bpayroll\b/i,
      /\bperformance review\b/i, /\bvisa paperwork\b/i,
    ],
  },
  {
    topic: 'healthcare',
    patterns: [
      /\bclinic\b/i, /\bhospital\b/i, /\bsurgery\b/i, /\bdiagnos(?:is|ed)\b/i,
      /\bmedication\b/i, /\bpatient\b/i, /\btherapist\b/i, /\brelapse\b/i,
      /\boverdose\b/i, /\bdementia\b/i, /\btreatment\b/i, /\bpregnant\b/i,
    ],
  },
  {
    topic: 'legal',
    patterns: [
      /\bcourt\b/i, /\bsue\b/i, /\bhearing\b/i, /\bpolice\b/i,
      /\bpulled over\b/i, /\bimmigration\b/i, /\blegal\b/i,
    ],
  },
  {
    topic: 'financial',
    patterns: [
      /\bmoney\b/i, /\bborrowed\b/i, /\bdebt\b/i, /\bmortgage\b/i,
      /\baccount\b/i, /\bcard\b/i, /\brent\b/i, /\bpay\b/i, /\bfraud\b/i,
    ],
  },
  {
    topic: 'family',
    patterns: [
      /\bdaughter\b/i, /\bson\b/i, /\bhusband\b/i, /\bwife\b/i,
      /\bpartner\b/i, /\bbrother\b/i, /\bsister\b/i, /\bmom\b/i,
      /\bmother\b/i, /\bfather\b/i, /\bparent\b/i, /\bcousin\b/i,
    ],
  },
  {
    topic: 'housing',
    patterns: [/\blandlord\b/i, /\bapartment\b/i, /\brent\b/i, /\bhome\b/i],
  },
  {
    topic: 'school',
    patterns: [/\bschool\b/i, /\bteacher\b/i, /\bprincipal\b/i, /\bsuspended\b/i],
  },
  {
    topic: 'safety',
    patterns: [/\bunsafe\b/i, /\bthreat(?:en|ened|ening)?\b/i, /\btrapped\b/i],
  },
];

const EMOTION_PHRASES: Record<Emotion, string> = {
  anger: 'angry',
  anxiety: 'anxious',
  confusion: 'confused',
  disgust: 'upset',
  excitement: 'excited',
  fear: 'afraid',
  frustration: 'frustrated',
  gratitude: 'grateful',
  hope: 'hopeful',
  joy: 'joyful',
  love: 'loving',
  peace: 'calm',
  sadness: 'sad',
  surprise: 'surprised',
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function significantTokens(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 4 && !PRIVACY_STOPWORDS.has(token));
}

function inferPrivateTopic(sourceText: string): string {
  const topics = TOPIC_PATTERNS
    .filter(({ patterns }) => patterns.some((pattern) => pattern.test(sourceText)))
    .map(({ topic }) => topic);

  const uniqueTopics = [...new Set(topics)].slice(0, 2);

  if (uniqueTopics.length === 0) {
    return 'personal';
  }

  return uniqueTopics.join(' and ');
}

function describeEmotions(emotions: Emotion[]): string {
  const phrases = emotions.map((emotion) => EMOTION_PHRASES[emotion]).filter(Boolean);

  if (phrases.length === 0) {
    return 'concerned';
  }

  if (phrases.length === 1) {
    return phrases[0];
  }

  return `${phrases[0]} and ${phrases[1]}`;
}

function buildAnonymizedFallback(sourceText: string, emotions: Emotion[]): string {
  return `The person is dealing with a private ${inferPrivateTopic(sourceText)} situation and feels ${describeEmotions(emotions)}.`;
}

function extractProtectedTerms(sourceText: string): string[] {
  const matches = sourceText.match(/\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b/g) ?? [];

  return [
    ...new Set(
      matches
        .map((match) => match.trim())
        .filter((match) => {
          const normalized = match.toLowerCase();
          return match.length >= 3 && !PROPER_NOUN_STOPWORDS.has(normalized);
        })
    ),
  ];
}

function containsProtectedTerm(candidate: string, sourceText: string): boolean {
  return extractProtectedTerms(sourceText).some((term) => {
    const pattern = new RegExp(`\\b${escapeRegExp(term)}\\b`, 'i');
    return pattern.test(candidate);
  });
}

function containsSensitivePattern(candidate: string): boolean {
  return SENSITIVE_PATTERNS.some((pattern) => pattern.test(candidate));
}

function containsSensitiveConcept(candidate: string): boolean {
  return SENSITIVE_CONCEPT_PATTERNS.some((pattern) => pattern.test(candidate));
}

function isTooSimilarToSource(candidate: string, sourceText: string): boolean {
  const candidateTokens = new Set(significantTokens(candidate));
  const sourceTokens = new Set(significantTokens(sourceText));

  if (candidateTokens.size < 5) {
    return false;
  }

  const overlap = [...candidateTokens].filter((token) => sourceTokens.has(token)).length;
  return overlap / candidateTokens.size >= 0.65;
}

function normalizeAnonymizedText(
  value: unknown,
  sourceText: string,
  emotions: Emotion[]
): string {
  if (typeof value !== 'string') {
    return buildAnonymizedFallback(sourceText, emotions);
  }

  const trimmed = value.trim().replace(/\s+/g, ' ');
  if (!trimmed) {
    return buildAnonymizedFallback(sourceText, emotions);
  }

  if (
    containsProtectedTerm(trimmed, sourceText) ||
    containsSensitivePattern(trimmed) ||
    containsSensitiveConcept(trimmed) ||
    isTooSimilarToSource(trimmed, sourceText)
  ) {
    return buildAnonymizedFallback(sourceText, emotions);
  }

  return trimmed;
}

function extractFirstJSONObject(text: string): string | null {
  let start = -1;
  let depth = 0;
  let inString = false;
  let isEscaped = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];

    if (start === -1) {
      if (char === '{') {
        start = index;
        depth = 1;
      }
      continue;
    }

    if (inString) {
      if (isEscaped) {
        isEscaped = false;
        continue;
      }

      if (char === '\\') {
        isEscaped = true;
        continue;
      }

      if (char === '"') {
        inString = false;
      }

      continue;
    }

    if (char === '"') {
      inString = true;
      continue;
    }

    if (char === '{') {
      depth += 1;
      continue;
    }

    if (char === '}') {
      depth -= 1;
      if (depth === 0) {
        return text.slice(start, index + 1);
      }
    }
  }

  return null;
}

function parseStructuredSentiment(text: string, sourceText: string): SentimentResult {
  const rawJSON = extractFirstJSONObject(text) ?? text;
  const parsed = JSON.parse(rawJSON) as RawSentimentResult;
  const emotions = normalizeEmotions(parsed.emotions);

  return {
    sentiment: normalizeSentiment(parsed.sentiment),
    emotions,
    confidence: normalizeConfidence(parsed.confidence),
    anonymizedText: normalizeAnonymizedText(parsed.anonymizedText, sourceText, emotions),
  };
}

export function useSentimentAnalyzer() {
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [raw, setRaw] = useState<RawSentimentResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (text: string) => {
    setResult(null);
    setRaw(null);
    setError(null);
    setIsAnalyzing(true);

    try {
      logSentimentDebug('analyze_start', { inputLength: text.length });
      const availability = await getTextModelAvailability();
      logSentimentDebug('model_availability', availability as Record<string, unknown>);
      if (availability.status !== 'available') {
        throw new Error(
          `Apple Intelligence not available: ${availability.reasonCode ?? 'unknown'}`
        );
      }

      try {
        const response = await generateObject<RawSentimentResult>({
          prompt: text,
          instructions: SENTIMENT_PROMPT,
          schema: SENTIMENT_SCHEMA,
        });

        const emotions = normalizeEmotions(response.object.emotions);

        setRaw({
          strategy: 'object',
          value: JSON.stringify(response.object, null, 2),
        });
        setResult({
          sentiment: normalizeSentiment(response.object.sentiment),
          emotions,
          confidence: normalizeConfidence(response.object.confidence),
          anonymizedText: normalizeAnonymizedText(response.object.anonymizedText, text, emotions),
        });
        logSentimentDebug('object_strategy_success');
      } catch (objectError) {
        logSentimentDebug('object_strategy_failed', {
          error: getErrorMessage(objectError),
        });
        const response = await generateText({
          prompt: text,
          instructions: SENTIMENT_PROMPT,
          temperature: 0.2,
          maxOutputTokens: 384,
        });

        setRaw({ strategy: 'text-fallback', value: response.text });
        const parseSummary = summarizeFallbackParse(response.text);
        logSentimentDebug('text_fallback_received', parseSummary);

        try {
          setResult(parseStructuredSentiment(response.text, text));
          logSentimentDebug('text_fallback_parse_success');
        } catch (parseError) {
          logSentimentDebug('text_fallback_parse_failed', {
            ...parseSummary,
            error: getErrorMessage(parseError),
          });
          throw new SentimentFallbackParseError(
            `Sentiment fallback returned non-JSON output. Open Debug -> sentiment + privacy to inspect raw model output. (${getErrorMessage(parseError)})`
          );
        }
      }
    } catch (e) {
      logSentimentDebug('analyze_failed', {
        error: getErrorMessage(e),
        type: e instanceof Error ? e.name : typeof e,
      });
      setError(
        e instanceof Error
          ? e.message
          : 'Sentiment analysis failed to return a usable result'
      );
    } finally {
      logSentimentDebug('analyze_done');
      setIsAnalyzing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setRaw(null);
    setError(null);
    setIsAnalyzing(false);
  }, []);

  return { result, raw, isAnalyzing, error, analyze, reset };
}
