import { describe, it, expect } from 'vitest';

import { buildLookupRequest } from '../lookup-request';

// Privacy boundary: the request that leaves the device must contain
// ONLY { appVariant, anonymizedText, sentiment, emotions, confidence } — never a
// transcript, audio path, recording duration, or device identifier.
const ALLOWED_KEYS = [
  'appVariant',
  'anonymizedText',
  'sentiment',
  'emotions',
  'confidence',
].sort();

describe('buildLookupRequest', () => {
  it('emits exactly the five whitelisted fields', () => {
    const req = buildLookupRequest('dhammapada', {
      anonymizedText: 'A person felt anxious about a decision.',
      sentiment: 'negative',
      emotions: ['anxiety', 'frustration'],
      confidence: 0.82,
    });
    expect(Object.keys(req).sort()).toEqual(ALLOWED_KEYS);
    expect(req.appVariant).toBe('dhammapada');
  });

  it('drops any extra fields carried by the on-device summary', () => {
    const leaky = {
      anonymizedText: 'A person felt restless.',
      sentiment: 'negative',
      emotions: ['anxiety'],
      confidence: 0.7,
      // Fields that must NEVER be sent — simulate a wider summary object.
      transcript: 'my name is Jane and I live at 12 Oak St',
      audioUri: 'file:///var/recordings/clip.m4a',
      durationSeconds: 37,
      deviceId: 'ABCD-1234',
    } as never;

    const req = buildLookupRequest('christian', leaky);
    expect(Object.keys(req).sort()).toEqual(ALLOWED_KEYS);
    expect(req as Record<string, unknown>).not.toHaveProperty('transcript');
    expect(req as Record<string, unknown>).not.toHaveProperty('audioUri');
    expect(req as Record<string, unknown>).not.toHaveProperty('durationSeconds');
    expect(req as Record<string, unknown>).not.toHaveProperty('deviceId');
  });

  it('preserves the emotions array contents', () => {
    const req = buildLookupRequest('dhammapada', {
      anonymizedText: 'x',
      sentiment: 'positive',
      emotions: ['gratitude', 'joy'],
      confidence: 0.9,
    });
    expect(req.emotions).toEqual(['gratitude', 'joy']);
  });
});
