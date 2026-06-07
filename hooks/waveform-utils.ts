// Pure helpers for the recording-screen waveform meter.
// No React or React Native dependencies — testable in any JS runtime.

export function emptyHistory(size: number): number[] {
  return new Array(size).fill(0);
}

// Append `level` to the rolling history and return a new array of length `size`
// (oldest sample dropped on the left, left-padded with zeros if too short).
// `level` is clamped to [0, 1]; non-finite values become 0.
export function pushSample(history: number[], level: number, size: number): number[] {
  const clamped = Number.isFinite(level) ? Math.max(0, Math.min(1, level)) : 0;
  const next = [...history, clamped];
  if (next.length > size) {
    return next.slice(next.length - size);
  }
  if (next.length < size) {
    return [...new Array(size - next.length).fill(0), ...next];
  }
  return next;
}
