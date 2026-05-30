// Pure, RN-free request shaping for the lookup call. Kept separate from
// lookup-client.ts (which imports expo-constants) so the privacy-critical
// request builder can be unit-tested under vitest without native deps.

export type AppVariant = 'christian' | 'stoic' | 'dhammapada';

// The ONLY fields that may leave the device. No audio, transcript, audio path,
// recording duration, or device identifier is ever part of this shape.
// buildLookupRequest below whitelists each field
// explicitly so a wider on-device summary object can never leak extra keys.
export type LookupRequest = {
  appVariant: AppVariant;
  anonymizedText: string;
  sentiment: string;
  emotions: string[];
  confidence: number;
};

// Minimal view of the on-device sentiment result this request is built from.
export type LookupRequestSource = {
  anonymizedText: string;
  sentiment: string;
  emotions: string[];
  confidence: number;
};

export function buildLookupRequest(
  appVariant: AppVariant,
  source: LookupRequestSource,
): LookupRequest {
  // Explicit field-by-field construction is the privacy guard: even if `source`
  // carries extra fields (raw model output, etc.), only these five are sent.
  return {
    appVariant,
    anonymizedText: source.anonymizedText,
    sentiment: source.sentiment,
    emotions: source.emotions,
    confidence: source.confidence,
  };
}
