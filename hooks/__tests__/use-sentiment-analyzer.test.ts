import { describe, it, expect } from 'vitest';
import {
  normalizeSentiment,
  normalizeEmotion,
  normalizeEmotions,
  normalizeConfidence,
  extractFirstJSONObject,
  parseStructuredSentiment,
  isTooSimilarToSource,
  containsProtectedTerm,
  normalizeAnonymizedText,
  buildAnonymizedFallback,
  hasUsableTranscriptSignal,
} from '../sentiment-utils';

// ── normalizeSentiment ──────────────────────────────────────────────────

describe('normalizeSentiment', () => {
  it('returns "positive" for exact match', () => {
    expect(normalizeSentiment('positive')).toBe('positive');
  });

  it('normalizes case and whitespace', () => {
    expect(normalizeSentiment('  Positive ')).toBe('positive');
  });

  it('resolves "mixed" alias to neutral', () => {
    expect(normalizeSentiment('mixed')).toBe('neutral');
  });

  it('falls back to neutral for unrecognized string', () => {
    expect(normalizeSentiment('garbage')).toBe('neutral');
  });

  it('returns neutral for non-string input', () => {
    expect(normalizeSentiment(42)).toBe('neutral');
  });
});

// ── normalizeEmotion ────────────────────────────────────────────────────

describe('normalizeEmotion', () => {
  it('returns the emotion for exact match', () => {
    expect(normalizeEmotion('joy')).toBe('joy');
  });

  it('resolves alias "sad" to "sadness"', () => {
    expect(normalizeEmotion('sad')).toBe('sadness');
  });

  it('resolves alias "happy" to "joy"', () => {
    expect(normalizeEmotion('happy')).toBe('joy');
  });

  it('returns null for unrecognized input', () => {
    expect(normalizeEmotion('nonexistent')).toBeNull();
  });
});

// ── normalizeEmotions ───────────────────────────────────────────────────

describe('normalizeEmotions', () => {
  it('deduplicates and normalizes an array', () => {
    expect(normalizeEmotions(['joy', 'joy', 'sad'])).toEqual(['joy', 'sadness']);
  });

  it('parses comma-separated string', () => {
    expect(normalizeEmotions('joy, fear')).toEqual(['joy', 'fear']);
  });

  it('returns empty array for non-array, non-string input', () => {
    expect(normalizeEmotions(null)).toEqual([]);
  });
});

// ── normalizeConfidence ─────────────────────────────────────────────────

describe('normalizeConfidence', () => {
  it('passes through a 0-1 number', () => {
    expect(normalizeConfidence(0.85)).toBeCloseTo(0.85);
  });

  it('divides by 100 when value > 1', () => {
    expect(normalizeConfidence(85)).toBeCloseTo(0.85);
  });

  it('parses percentage string', () => {
    expect(normalizeConfidence('85%')).toBeCloseTo(0.85);
  });

  it('clamps to [0, 1]', () => {
    expect(normalizeConfidence(-0.5)).toBe(0);
    // Values > 1 are treated as percentages (divided by 100), then clamped
    expect(normalizeConfidence(1.5)).toBeCloseTo(0.015);
  });

  it('returns 0.5 fallback for unparseable input', () => {
    expect(normalizeConfidence('abc')).toBe(0.5);
  });
});

// ── extractFirstJSONObject ──────────────────────────────────────────────

describe('extractFirstJSONObject', () => {
  it('extracts simple JSON object', () => {
    expect(extractFirstJSONObject('{"a":1}')).toBe('{"a":1}');
  });

  it('finds JSON embedded in surrounding text', () => {
    expect(extractFirstJSONObject('text {"a":1} more')).toBe('{"a":1}');
  });

  it('handles nested objects', () => {
    expect(extractFirstJSONObject('{"a":{"b":2}}')).toBe('{"a":{"b":2}}');
  });

  it('returns null when no object found', () => {
    expect(extractFirstJSONObject('no braces here')).toBeNull();
  });

  it('returns null for unclosed brace', () => {
    expect(extractFirstJSONObject('{"a":1')).toBeNull();
  });
});

// ── parseStructuredSentiment ────────────────────────────────────────────

describe('parseStructuredSentiment', () => {
  it('parses valid JSON into SentimentResult', () => {
    const input = JSON.stringify({
      sentiment: 'negative',
      emotions: ['sadness', 'anxiety'],
      confidence: 0.8,
      anonymizedText: 'the person feels overwhelmed',
    });
    const result = parseStructuredSentiment(input, 'i am so sad and worried');
    expect(result.sentiment).toBe('negative');
    expect(result.emotions).toEqual(['sadness', 'anxiety']);
    expect(result.confidence).toBeCloseTo(0.8);
    expect(result.anonymizedText).toBe('the person feels overwhelmed');
  });
});

// ── isTooSimilarToSource ────────────────────────────────────────────────

describe('isTooSimilarToSource', () => {
  it('returns true when most significant tokens overlap and count >= 5', () => {
    const source = 'my manager john yelled at me today about the project deadline';
    const candidate = 'the manager yelled at me today about a project';
    // Both have ≥5 significant tokens, and candidate has ~71% overlap with source tokens
    expect(isTooSimilarToSource(candidate, source)).toBe(true);
  });

  it('returns false when candidate differs sufficiently', () => {
    const source = 'My manager John at Acme Corp yelled at me today';
    const candidate = 'the person had a difficult interaction at work';
    expect(isTooSimilarToSource(candidate, source)).toBe(false);
  });

  it('returns false for short candidate (< 5 significant tokens)', () => {
    expect(isTooSimilarToSource('hi there', 'hello world')).toBe(false);
  });
});

// ── containsProtectedTerm ───────────────────────────────────────────────

describe('containsProtectedTerm', () => {
  it('detects name from source in candidate', () => {
    expect(containsProtectedTerm('John was upset', 'My manager John yelled')).toBe(true);
  });

  it('returns false when no name present', () => {
    expect(containsProtectedTerm('the person was upset', 'My manager yelled')).toBe(false);
  });
});

// ── buildAnonymizedFallback ─────────────────────────────────────────────

describe('buildAnonymizedFallback', () => {
  it('describes a workplace situation', () => {
    const result = buildAnonymizedFallback('my boss yelled at me', ['anger']);
    expect(result).toMatch(/workplace/);
    expect(result).toMatch(/angry/);
  });

  it('produces generic fallback when no topic matches', () => {
    const result = buildAnonymizedFallback('i feel great', ['joy']);
    expect(result).toMatch(/personal/);
    expect(result).toMatch(/joyful/);
  });
});

// ── hasUsableTranscriptSignal ───────────────────────────────────────────

describe('hasUsableTranscriptSignal', () => {
  it('rejects empty or filler-only transcripts', () => {
    expect(hasUsableTranscriptSignal('')).toBe(false);
    expect(hasUsableTranscriptSignal('uh um hmm')).toBe(false);
    expect(hasUsableTranscriptSignal('I am')).toBe(false);
  });

  it('rejects common keyboard-mash transcripts', () => {
    expect(hasUsableTranscriptSignal('asdf qwer zxcv')).toBe(false);
  });

  it('accepts short but meaningful emotional input', () => {
    expect(hasUsableTranscriptSignal('sad')).toBe(true);
    expect(hasUsableTranscriptSignal('I feel anxious')).toBe(true);
  });
});

// ── normalizeAnonymizedText ─────────────────────────────────────────────

describe('normalizeAnonymizedText', () => {
  it('passes through clean anonymized text', () => {
    const result = normalizeAnonymizedText(
      'the person feels overwhelmed by work',
      'My boss John at Acme Corp yelled at me',
      ['frustration']
    );
    expect(result).toBe('the person feels overwhelmed by work');
  });

  it('falls back when candidate contains a protected term from source', () => {
    const result = normalizeAnonymizedText(
      'John was upset',
      'My manager John yelled at me',
      ['anger']
    );
    expect(result).toMatch(/private/);
    expect(result).toMatch(/workplace/);
  });

  it('returns fallback for non-string value', () => {
    const result = normalizeAnonymizedText(null, 'some source text', ['sadness']);
    expect(result).toMatch(/personal/);
  });
});
