// Per-variant brand tokens. The Christian build ships as "Freely Spoken", the
// Buddhist (Dhammapada) build as "Idle Ashes". Stoic is an unreleased stub and
// reuses the Freely Spoken palette. Freely Spoken remains the default brand.
import type { AppVariant } from '@/services/lookup-request';

export type BrandPalette = {
  primary: string;
  accent: string;
  background: string;
  surface: string;
  softSurface: string;
  text: string;
  muted: string;
  destructive: string;
  darkSurface: string;
  inverseText: string;
};

export type BrandTokens = {
  name: string;
  wordmark: string;
  colors: BrandPalette;
};

const FREELY_SPOKEN_TOKENS: BrandTokens = {
  name: 'Freely Spoken',
  wordmark: 'Freely Spoken',
  colors: {
    primary: '#172235',
    accent: '#B18A55',
    background: '#F7F1E8',
    surface: '#EFE4D3',
    softSurface: 'rgba(23,34,53,0.05)',
    text: '#111827',
    muted: '#6B6257',
    destructive: '#B94034',
    darkSurface: '#0F1724',
    inverseText: '#F7F1E8',
  },
};

const BRANDS: Record<AppVariant, BrandTokens> = {
  christian: FREELY_SPOKEN_TOKENS,
  dhammapada: {
    name: 'Idle Ashes',
    wordmark: 'idle ashes',
    colors: {
      primary: '#2B2A25',
      accent: '#C1784A',
      background: '#F4EEE6',
      surface: '#E9DFD2',
      softSurface: 'rgba(43,42,37,0.06)',
      text: '#24231F',
      muted: '#7C756B',
      destructive: '#B94034',
      darkSurface: '#181714',
      inverseText: '#F4EEE6',
    },
  },
  stoic: {
    ...FREELY_SPOKEN_TOKENS,
    name: 'Freely Spoken (Stoic)',
  },
};

export function getBrand(appVariant: string): BrandTokens {
  if (appVariant === 'dhammapada') return BRANDS.dhammapada;
  if (appVariant === 'stoic') return BRANDS.stoic;
  return BRANDS.christian;
}

export function getBrandName(appVariant: string): string {
  return getBrand(appVariant).name;
}

// Default global brand (Freely Spoken). Variant-aware screens should call
// getBrand(appVariant) instead of reading this directly.
export const Brand = BRANDS.christian;
