import { useState, useCallback } from 'react';
import {
  generateObject,
  getTextModelAvailability,
} from '@ratley/react-native-apple-foundation-models';
import type { JSONSchema } from '@ratley/react-native-apple-foundation-models';

const SENTIMENTS = ['positive', 'negative', 'neutral'] as const;

const EMOTIONS = [
  'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
  'hope', 'anxiety', 'peace', 'love', 'gratitude', 'frustration',
  'excitement', 'confusion',
] as const;

const SENTIMENT_SCHEMA = {
  type: 'object',
  required: ['sentiment', 'emotions', 'confidence'],
  properties: {
    sentiment: {
      type: 'string',
      enum: [...SENTIMENTS],
    },
    emotions: {
      type: 'array',
      items: { type: 'string', enum: [...EMOTIONS] },
    },
    confidence: {
      type: 'number',
      minimum: 0,
      maximum: 1,
    },
  },
} satisfies JSONSchema;

export type SentimentResult = {
  sentiment: (typeof SENTIMENTS)[number];
  emotions: (typeof EMOTIONS)[number][];
  confidence: number;
};

export function useSentimentAnalyzer() {
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (text: string) => {
    setResult(null);
    setError(null);
    setIsAnalyzing(true);

    try {
      const availability = await getTextModelAvailability();
      if (availability.status !== 'available') {
        throw new Error(
          `Apple Intelligence not available: ${availability.reasonCode ?? 'unknown'}`
        );
      }

      const response = await generateObject<SentimentResult>({
        prompt: text,
        instructions: `You are a sentiment analyzer. Given text, classify its sentiment and emotions.

Return:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: ${EMOTIONS.join(', ')}
- confidence: a number between 0 and 1 indicating how confident you are

Do NOT repeat or paraphrase any of the input text.`,
        schema: SENTIMENT_SCHEMA,
      });

      setResult(response.object);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsAnalyzing(false);
  }, []);

  return { result, isAnalyzing, error, analyze, reset };
}
