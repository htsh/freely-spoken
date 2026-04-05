import { useState, useCallback } from 'react';
import {
  generateObject,
  getTextModelAvailability,
} from '@ratley/react-native-apple-foundation-models';

const EMOTIONS = [
  'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
  'hope', 'anxiety', 'peace', 'love', 'gratitude', 'frustration',
  'excitement', 'confusion',
] as const;

const SENTIMENT_SCHEMA = {
  type: 'object' as const,
  required: ['sentiment', 'emotions', 'confidence'],
  properties: {
    sentiment: {
      type: 'string' as const,
    },
    emotions: {
      type: 'array' as const,
      items: { type: 'string' as const },
    },
    confidence: {
      type: 'number' as const,
      minimum: 0,
      maximum: 1,
    },
  },
};

export type SentimentResult = {
  sentiment: 'positive' | 'negative' | 'neutral';
  emotions: string[];
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

      const response = await generateObject({
        prompt: text,
        instructions: `You are a sentiment analyzer. Given text, classify its sentiment and emotions.

Return:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: ${EMOTIONS.join(', ')}
- confidence: a number between 0 and 1 indicating how confident you are

Do NOT repeat or paraphrase any of the input text.`,
        schema: SENTIMENT_SCHEMA,
        temperature: 0.2,
      });

      setResult(response as SentimentResult);
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
