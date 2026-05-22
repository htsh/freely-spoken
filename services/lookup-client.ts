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

const CLIENT_REQUEST_ID_HEADER = 'X-Client-Request-ID';
const SERVER_REQUEST_ID_HEADER = 'X-Lookup-Request-ID';
const ENV_CONFIG: Record<string, string | undefined> = {
  lookupApiUrl: process.env.EXPO_PUBLIC_LOOKUP_API_URL,
  lookupClientSecret: process.env.EXPO_PUBLIC_LOOKUP_CLIENT_SECRET,
  appVariant: process.env.EXPO_PUBLIC_APP_VARIANT,
};

export class MissingLookupApiUrlError extends Error {
  constructor() {
    super(
      'LOOKUP_API_URL is not configured. Set EXPO_PUBLIC_LOOKUP_API_URL before building, ' +
      'or set "lookupApiUrl" in app.json -> extra.',
    );
    this.name = 'MissingLookupApiUrlError';
  }
}

function logLookupDebug(event: string, details?: Record<string, unknown>): void {
  if (!__DEV__) {
    return;
  }
  if (details) {
    console.log('[lookup]', event, details);
    return;
  }
  console.log('[lookup]', event);
}

function buildClientRequestId(): string {
  return `ios-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function buildCorrelationSuffix(clientRequestId: string, serverRequestId?: string | null): string {
  return serverRequestId
    ? ` [clientRequestId=${clientRequestId}; serverRequestId=${serverRequestId}]`
    : ` [clientRequestId=${clientRequestId}]`;
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
  const fromExtra = typeof value === 'string' ? value.trim() : '';

  // app.json may still expose literal "$EXPO_PUBLIC_*" placeholders in some
  // local native run flows. Prefer concrete extra values, then fall back to
  // EXPO_PUBLIC_* variables in JS bundle.
  if (fromExtra && !fromExtra.startsWith('$')) {
    return fromExtra;
  }

  const fromEnv = ENV_CONFIG[key];
  if (typeof fromEnv !== 'string') return undefined;
  const trimmedEnv = fromEnv.trim();
  if (!trimmedEnv || trimmedEnv.startsWith('$')) return undefined;
  return trimmedEnv;
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
  const clientRequestId = buildClientRequestId();
  const endpoint = `${url.replace(/\/$/, '')}/lookup`;

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (secret) headers['X-Lookup-Client-Secret'] = secret;
  headers[CLIENT_REQUEST_ID_HEADER] = clientRequestId;

  logLookupDebug('request_start', {
    clientRequestId,
    endpoint,
    appVariant: req.appVariant,
    sentiment: req.sentiment,
    emotions: req.emotions,
    confidence: req.confidence,
    anonymizedTextLength: req.anonymizedText.length,
  });

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers,
      body: JSON.stringify(req),
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : 'network error';
    logLookupDebug('request_network_error', {
      clientRequestId,
      error: message,
    });
    throw new LookupError(
      'network_error',
      `${message}${buildCorrelationSuffix(clientRequestId, null)}`,
      0
    );
  }

  const serverRequestId = response.headers.get(SERVER_REQUEST_ID_HEADER);
  const responseText = await response.text();
  logLookupDebug('response_received', {
    clientRequestId,
    serverRequestId,
    status: response.status,
    bodyLength: responseText.length,
  });

  let body: unknown;
  try {
    body = JSON.parse(responseText) as unknown;
  } catch {
    logLookupDebug('response_parse_failed', {
      clientRequestId,
      serverRequestId,
      status: response.status,
      firstNonWhitespaceChar: responseText.trim().charAt(0) || null,
    });
    throw new LookupError(
      'bad_response',
      `Lookup server returned non-JSON (HTTP ${response.status})${buildCorrelationSuffix(clientRequestId, serverRequestId)}`,
      response.status,
    );
  }

  if (!response.ok) {
    const err = (body as { error?: { code?: string; message?: string } })?.error;
    const code = err?.code ?? 'unknown';
    const message = err?.message ?? `HTTP ${response.status}`;
    logLookupDebug('response_error', {
      clientRequestId,
      serverRequestId,
      status: response.status,
      code,
      message,
    });
    throw new LookupError(
      code,
      `${message}${buildCorrelationSuffix(clientRequestId, serverRequestId)}`,
      response.status
    );
  }

  logLookupDebug('response_ok', {
    clientRequestId,
    serverRequestId,
    status: response.status,
  });
  return body as LookupResult;
}

export function getBuildAppVariant(): AppVariant {
  const v = readConfig('appVariant');
  return v === 'stoic' ? 'stoic' : 'christian';
}
