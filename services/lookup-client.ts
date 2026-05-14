import Constants from 'expo-constants';

export type AppVariant = 'christian' | 'stoic';

export type LookupRequest = {
  appVariant: AppVariant;
  anonymizedText: string;
  sentiment: string;
  emotions: string[];
  confidence: number;
};

export type Reference = {
  ref: string;
  shortReason: string;
  text?: string | null;
  translation?: string | null;
  textError?: string | null;
};

export type ChristianLookupResult = {
  primary: Reference;
  alternates: Reference[];
  provider: string;
  model: string;
  retryCount: number;
  fallbackUsed: boolean;
  crisisFlag: boolean;
};

export type StoicStubResult = {
  status: 'not_implemented';
  appVariant: 'stoic';
  message: string;
  crisisFlag: boolean;
};

export type LookupResult = ChristianLookupResult | StoicStubResult;

export class MissingLookupApiUrlError extends Error {
  constructor() {
    super(
      'LOOKUP_API_URL is not configured. Set EXPO_PUBLIC_LOOKUP_API_URL before building, ' +
      'or set "lookupApiUrl" in app.json -> extra.',
    );
    this.name = 'MissingLookupApiUrlError';
  }
}

export class LookupError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = 'LookupError';
    this.code = code;
    this.status = status;
  }
}

function readConfig(key: string): string | undefined {
  const extra = Constants.expoConfig?.extra as Record<string, unknown> | undefined;
  const value = extra?.[key];
  if (typeof value !== 'string') return undefined;
  // EAS substitutes $EXPO_PUBLIC_* at build time. If a placeholder leaks
  // through unmodified, treat it as unset rather than sending "$..." as a URL.
  if (value.startsWith('$')) return undefined;
  return value || undefined;
}

export function isStoicStub(result: LookupResult): result is StoicStubResult {
  return (result as StoicStubResult).status === 'not_implemented';
}

export async function lookupSpiritualResponse(req: LookupRequest): Promise<LookupResult> {
  const url = readConfig('lookupApiUrl');
  if (!url) {
    throw new MissingLookupApiUrlError();
  }
  const secret = readConfig('lookupClientSecret');

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (secret) headers['X-Lookup-Client-Secret'] = secret;

  let response: Response;
  try {
    response = await fetch(`${url.replace(/\/$/, '')}/lookup`, {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'network error';
    throw new LookupError('network_error', message, 0);
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new LookupError(
      'bad_response',
      `Lookup server returned non-JSON (HTTP ${response.status})`,
      response.status,
    );
  }

  if (!response.ok) {
    const err = (body as { error?: { code?: string; message?: string } })?.error;
    const code = err?.code ?? 'unknown';
    const message = err?.message ?? `HTTP ${response.status}`;
    throw new LookupError(code, message, response.status);
  }

  return body as LookupResult;
}

export function getBuildAppVariant(): AppVariant {
  const v = readConfig('appVariant');
  return v === 'stoic' ? 'stoic' : 'christian';
}
