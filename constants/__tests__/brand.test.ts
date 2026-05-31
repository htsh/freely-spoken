import { describe, expect, it } from 'vitest';

import { getBrand, getBrandName } from '../brand';

describe('variant brand tokens', () => {
  it('keeps Freely Spoken as the default brand', () => {
    expect(getBrandName('christian')).toBe('Freely Spoken');
    expect(getBrand('unknown').colors.primary).toBe('#172235');
  });

  it('returns Idle Ashes tokens for the dhammapada variant', () => {
    const brand = getBrand('dhammapada');
    expect(brand.name).toBe('Idle Ashes');
    expect(brand.wordmark).toBe('idle ashes');
    expect(brand.colors.background).toBe('#F4EEE6');
    expect(brand.colors.primary).toBe('#2B2A25');
  });
});
