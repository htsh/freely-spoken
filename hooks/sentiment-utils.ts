// Pure functions for parsing and normalizing sentiment-analysis model output.
// No React or React Native dependencies — testable in any JS runtime.

import type { JSONSchema } from '@ratley/react-native-apple-foundation-models';

// ── Constants ──────────────────────────────────────────────────────────

export const SENTIMENTS = ['positive', 'negative', 'neutral'] as const;

export const EMOTIONS = [
  'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
  'hope', 'anxiety', 'peace', 'love', 'gratitude', 'frustration',
  'excitement', 'confusion',
] as const;

export type Sentiment = (typeof SENTIMENTS)[number];
export type Emotion = (typeof EMOTIONS)[number];

export type RawSentimentResult = {
  sentiment?: unknown;
  emotions?: unknown;
  confidence?: unknown;
  anonymizedText?: unknown;
};

export const SENTIMENT_SCHEMA = {
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

const LOW_SIGNAL_TRANSCRIPT_TOKENS = new Set([
  'ah', 'aha', 'am', 'be', 'been', 'being', 'blah', 'blahblah', 'da',
  'eh', 'er', 'feel', 'feeling', 'felt', 'hm', 'hmm', 'hmmm', 'la',
  'like', 'mm', 'mmm', 'na', 'ok', 'okay', 'test', 'testing', 'uh',
  'uhh', 'um', 'umm', 'ummm',
]);

const KEYBOARD_MASH_PATTERNS = [
  /^(?:a?sdf+|dfgh+|fdsa+|ghjk+|hjkl+|jkl+|lkj+|qwer+|zxcv+)$/,
];

// ── Pure functions ──────────────────────────────────────────────────────

export function normalizeLabel(value: string): string {
  return value.trim().toLowerCase().replace(/[^a-z\s-]/g, '').replace(/\s+/g, ' ');
}

export function normalizeSentiment(value: unknown): Sentiment {
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

export function normalizeEmotion(value: string): Emotion | null {
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

export function normalizeEmotions(value: unknown): Emotion[] {
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

export function normalizeConfidence(value: unknown): number {
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

export function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function significantTokens(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((token) => token.length >= 4 && !PRIVACY_STOPWORDS.has(token));
}

export function inferPrivateTopic(sourceText: string): string {
  const topics = TOPIC_PATTERNS
    .filter(({ patterns }) => patterns.some((pattern) => pattern.test(sourceText)))
    .map(({ topic }) => topic);

  const uniqueTopics = [...new Set(topics)].slice(0, 2);

  if (uniqueTopics.length === 0) {
    return 'personal';
  }

  return uniqueTopics.join(' and ');
}

export function describeEmotions(emotions: Emotion[]): string {
  const phrases = emotions.map((emotion) => EMOTION_PHRASES[emotion]).filter(Boolean);

  if (phrases.length === 0) {
    return 'concerned';
  }

  if (phrases.length === 1) {
    return phrases[0];
  }

  return `${phrases[0]} and ${phrases[1]}`;
}

export function buildAnonymizedFallback(sourceText: string, emotions: Emotion[]): string {
  return `The person is dealing with a private ${inferPrivateTopic(sourceText)} situation and feels ${describeEmotions(emotions)}.`;
}

export function hasUsableTranscriptSignal(value: string): boolean {
  const tokens = value
    .toLowerCase()
    .match(/[a-z0-9']+/g) ?? [];

  return tokens.some((token) => {
    const normalized = token.replace(/^'+|'+$/g, '');
    if (
      normalized.length <= 1 ||
      PRIVACY_STOPWORDS.has(normalized) ||
      LOW_SIGNAL_TRANSCRIPT_TOKENS.has(normalized) ||
      /^\d+$/.test(normalized) ||
      !/[a-z]/.test(normalized)
    ) {
      return false;
    }

    return !KEYBOARD_MASH_PATTERNS.some((pattern) => pattern.test(normalized));
  });
}

export function extractProtectedTerms(sourceText: string): string[] {
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

export function containsProtectedTerm(candidate: string, sourceText: string): boolean {
  return extractProtectedTerms(sourceText).some((term) => {
    const pattern = new RegExp(`\\b${escapeRegExp(term)}\\b`, 'i');
    return pattern.test(candidate);
  });
}

export function containsSensitivePattern(candidate: string): boolean {
  return SENSITIVE_PATTERNS.some((pattern) => pattern.test(candidate));
}

export function containsSensitiveConcept(candidate: string): boolean {
  return SENSITIVE_CONCEPT_PATTERNS.some((pattern) => pattern.test(candidate));
}

export function isTooSimilarToSource(candidate: string, sourceText: string): boolean {
  const candidateTokens = new Set(significantTokens(candidate));
  const sourceTokens = new Set(significantTokens(sourceText));

  if (candidateTokens.size < 5) {
    return false;
  }

  const overlap = [...candidateTokens].filter((token) => sourceTokens.has(token)).length;
  return overlap / candidateTokens.size >= 0.65;
}

export function normalizeAnonymizedText(
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

export function extractFirstJSONObject(text: string): string | null {
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

export function parseStructuredSentiment(text: string, sourceText: string): SentimentResult {
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
