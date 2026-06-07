import { describe, it, expect } from 'vitest';
import { emptyHistory, pushSample } from '../waveform-utils';

describe('emptyHistory', () => {
  it('returns an array of the requested length filled with zeros', () => {
    expect(emptyHistory(4)).toEqual([0, 0, 0, 0]);
  });
});

describe('pushSample', () => {
  it('appends the newest sample at the end and keeps the array full-width', () => {
    const result = pushSample([0, 0, 0, 0], 0.5, 4);
    expect(result).toEqual([0, 0, 0, 0.5]);
  });

  it('drops the oldest sample from the left when at capacity', () => {
    const result = pushSample([0.1, 0.2, 0.3, 0.4], 0.9, 4);
    expect(result).toEqual([0.2, 0.3, 0.4, 0.9]);
  });

  it('left-pads with zeros when the history is shorter than size', () => {
    const result = pushSample([], 0.7, 3);
    expect(result).toEqual([0, 0, 0.7]);
  });

  it('clamps out-of-range levels into [0, 1]', () => {
    expect(pushSample([0, 0], 1.8, 2)).toEqual([0, 1]);
    expect(pushSample([0, 0], -0.5, 2)).toEqual([0, 0]);
  });

  it('treats non-finite levels as 0', () => {
    expect(pushSample([0.4, 0.4], Number.NaN, 2)).toEqual([0.4, 0]);
  });

  it('does not mutate the input array', () => {
    const input = [0.1, 0.2];
    pushSample(input, 0.3, 2);
    expect(input).toEqual([0.1, 0.2]);
  });
});
