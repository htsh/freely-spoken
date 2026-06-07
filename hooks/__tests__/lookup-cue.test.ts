import { describe, it, expect } from 'vitest';
import { buildLookupCaptions } from '../lookup-cue';

describe('buildLookupCaptions', () => {
  it('substitutes the noun into the first and third lines (verse)', () => {
    expect(buildLookupCaptions('verse')).toEqual([
      'Finding your verse',
      'Reading your reflection',
      'Choosing a fitting verse',
      'Almost there…',
    ]);
  });

  it('substitutes the noun into the first and third lines (passage)', () => {
    expect(buildLookupCaptions('passage')).toEqual([
      'Finding your passage',
      'Reading your reflection',
      'Choosing a fitting passage',
      'Almost there…',
    ]);
  });
});
