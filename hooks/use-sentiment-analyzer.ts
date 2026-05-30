import { useState, useCallback } from 'react';
import {
  generateObject,
  generateText,
  getTextModelAvailability,
} from '@ratley/react-native-apple-foundation-models';

import {
  SentimentResult,
  RawSentimentResult,
  SENTIMENT_SCHEMA,
  normalizeSentiment,
  normalizeEmotions,
  normalizeConfidence,
  normalizeAnonymizedText,
  parseStructuredSentiment,
  extractFirstJSONObject,
} from './sentiment-utils';

const SENTIMENT_PROMPT = `You are a privacy-first sentiment analyzer. Given text, classify its sentiment and emotions.

Return a single JSON object with:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: joy, sadness, anger, fear, surprise, disgust, hope, anxiety, peace, love, gratitude, frustration, excitement, confusion
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

export type RawSentimentResponse = {
  /** Which path produced this output. `text-fallback` means generateObject failed and we re-asked with generateText. */
  strategy: 'object' | 'text-fallback';
  /** Pretty-printed model output (object stringified, or raw text for the fallback path). */
  value: string;
};

class SentimentFallbackParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SentimentFallbackParseError';
  }
}

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
