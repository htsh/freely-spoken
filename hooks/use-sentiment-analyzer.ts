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

function normalizeAnonymizedText(value: unknown): string {
  if (typeof value !== 'string') {
    return 'The person is dealing with a personal situation and wants advice while keeping identifying details private.';
  }

  const trimmed = value.trim().replace(/\s+/g, ' ');
  if (!trimmed) {
    return 'The person is dealing with a personal situation and wants advice while keeping identifying details private.';
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

function parseStructuredSentiment(text: string): SentimentResult {
  const rawJSON = extractFirstJSONObject(text) ?? text;
  const parsed = JSON.parse(rawJSON) as RawSentimentResult;

  return {
    sentiment: normalizeSentiment(parsed.sentiment),
    emotions: normalizeEmotions(parsed.emotions),
    confidence: normalizeConfidence(parsed.confidence),
    anonymizedText: normalizeAnonymizedText(parsed.anonymizedText),
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
      const availability = await getTextModelAvailability();
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

        setRaw({
          strategy: 'object',
          value: JSON.stringify(response.object, null, 2),
        });
        setResult({
          sentiment: normalizeSentiment(response.object.sentiment),
          emotions: normalizeEmotions(response.object.emotions),
          confidence: normalizeConfidence(response.object.confidence),
          anonymizedText: normalizeAnonymizedText(response.object.anonymizedText),
        });
      } catch {
        const response = await generateText({
          prompt: text,
          instructions: SENTIMENT_PROMPT,
          temperature: 0.2,
          maxOutputTokens: 384,
        });

        setRaw({ strategy: 'text-fallback', value: response.text });
        setResult(parseStructuredSentiment(response.text));
      }
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : 'Sentiment analysis failed to return a usable result'
      );
    } finally {
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
