import { useCallback, useState } from 'react';

import {
  LookupError,
  LookupRequest,
  LookupResult,
  MissingLookupApiUrlError,
  lookupSpiritualResponse,
} from '@/services/lookup-client';

export function useSpiritualResponseLookup() {
  const [result, setResult] = useState<LookupResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lookup = useCallback(async (req: LookupRequest) => {
    setResult(null);
    setError(null);
    setIsLoading(true);
    try {
      const payload = await lookupSpiritualResponse(req);
      setResult(payload);
    } catch (e) {
      if (e instanceof LookupError) {
        setError(e.message);
      } else if (e instanceof MissingLookupApiUrlError) {
        setError(e.message);
      } else if (e instanceof Error) {
        setError(e.message);
      } else {
        setError('Lookup failed for an unknown reason');
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return { result, isLoading, error, lookup, reset };
}
