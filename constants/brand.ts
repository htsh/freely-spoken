// Per-variant product name. The Christian build ships as "Freely Spoken", the
// Buddhist (Dhammapada) build as "Idle Ashes". Stoic is an unreleased stub and
// reuses the default. Colors are shared across variants.
const BRAND_NAMES: Record<string, string> = {
  christian: 'Freely Spoken',
  dhammapada: 'Idle Ashes',
};

export function getBrandName(appVariant: string): string {
  return BRAND_NAMES[appVariant] ?? 'Freely Spoken';
}

export const Brand = {
  name: 'Freely Spoken',
  colors: {
    navy: '#172235',
    gold: '#B18A55',
    ivory: '#F7F1E8',
    parchment: '#EFE4D3',
    ink: '#111827',
    muted: '#6B6257',
    destructive: '#B94034',
    darkSurface: '#0F1724',
  },
} as const;
