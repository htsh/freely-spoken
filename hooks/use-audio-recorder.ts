import { useState, useRef, useCallback, useEffect } from 'react';
import { AppState as RNAppState, type AppStateStatus } from 'react-native';
import { Audio } from 'expo-av';

type RecorderState = 'idle' | 'recording';

const STATUS_UPDATE_INTERVAL_MS = 120;
const MIN_METER_DB = -60;
const NOISE_GATE = 0.06;
const ATTACK_SMOOTHING = 0.45;
const RELEASE_SMOOTHING = 0.18;
const APP_ACTIVE_WAIT_TIMEOUT_MS = 3000;
const AUDIO_SESSION_FOREGROUND_SETTLE_MS = 300;
const AUDIO_SESSION_RETRY_SETTLE_MS = 500;
const MAX_AUDIO_ACTIVATION_ATTEMPTS = 2;
const BACKGROUND_AUDIO_SESSION_MESSAGE =
  'The microphone is not ready yet. Keep the app open and try again.';

function normalizeInputLevel(metering?: number): number {
  if (typeof metering !== 'number' || Number.isNaN(metering)) return 0;

  const clampedDb = Math.max(MIN_METER_DB, Math.min(0, metering));
  const normalized = (clampedDb - MIN_METER_DB) / Math.abs(MIN_METER_DB);
  return normalized < NOISE_GATE ? 0 : normalized;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isActiveAppState(state: AppStateStatus | null): boolean {
  return state === 'active';
}

async function waitForActiveAppState(): Promise<void> {
  if (isActiveAppState(RNAppState.currentState)) {
    await sleep(AUDIO_SESSION_FOREGROUND_SETTLE_MS);
    return;
  }

  await new Promise<void>((resolve, reject) => {
    let subscription: ReturnType<typeof RNAppState.addEventListener> | null = null;
    let timeout: ReturnType<typeof setTimeout> | null = null;

    const cleanup = () => {
      if (timeout) clearTimeout(timeout);
      subscription?.remove();
    };

    timeout = setTimeout(() => {
      cleanup();
      reject(new Error(BACKGROUND_AUDIO_SESSION_MESSAGE));
    }, APP_ACTIVE_WAIT_TIMEOUT_MS);

    subscription = RNAppState.addEventListener('change', (nextState) => {
      if (!isActiveAppState(nextState)) return;
      cleanup();
      resolve();
    });

    if (isActiveAppState(RNAppState.currentState)) {
      cleanup();
      resolve();
    }
  });

  await sleep(AUDIO_SESSION_FOREGROUND_SETTLE_MS);
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function isBackgroundAudioSessionError(error: unknown): boolean {
  const message = getErrorMessage(error);
  return message.includes('currently in the background')
    && message.includes('audio session could not be activated');
}

async function retryAfterForegroundSettles(): Promise<void> {
  await waitForActiveAppState();
  await sleep(AUDIO_SESSION_RETRY_SETTLE_MS);
}

async function prepareRecording(): Promise<Audio.Recording> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= MAX_AUDIO_ACTIVATION_ATTEMPTS; attempt += 1) {
    const recording = new Audio.Recording();

    try {
      await recording.prepareToRecordAsync({
        ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
        keepAudioActiveHint: true,
      });
      return recording;
    } catch (error) {
      lastError = error;
      if (!isBackgroundAudioSessionError(error) || attempt === MAX_AUDIO_ACTIVATION_ATTEMPTS) {
        break;
      }
      await retryAfterForegroundSettles();
    }
  }

  if (isBackgroundAudioSessionError(lastError)) {
    throw new Error(BACKGROUND_AUDIO_SESSION_MESSAGE);
  }

  throw lastError;
}

async function startPreparedRecording(recording: Audio.Recording): Promise<void> {
  try {
    await recording.startAsync();
  } catch (error) {
    if (!isBackgroundAudioSessionError(error)) {
      throw error;
    }

    await retryAfterForegroundSettles();

    try {
      await recording.startAsync();
    } catch (retryError) {
      if (isBackgroundAudioSessionError(retryError)) {
        throw new Error(BACKGROUND_AUDIO_SESSION_MESSAGE);
      }
      throw retryError;
    }
  }
}

export function useAudioRecorder() {
  const [state, setState] = useState<RecorderState>('idle');
  const [duration, setDuration] = useState(0);
  const [inputLevel, setInputLevel] = useState(0);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const inputLevelRef = useRef(0);

  const cleanup = useCallback(() => {
    if (recordingRef.current) {
      recordingRef.current.setOnRecordingStatusUpdate(null);
      recordingRef.current.stopAndUnloadAsync().catch(() => {});
      recordingRef.current = null;
    }
    inputLevelRef.current = 0;
    setInputLevel(0);
  }, []);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const startRecording = useCallback(async () => {
    const { granted } = await Audio.requestPermissionsAsync();
    if (!granted) {
      throw new Error('Microphone permission not granted');
    }

    await waitForActiveAppState();

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
      staysActiveInBackground: false,
    });

    const recording = await prepareRecording();

    setDuration(0);
    inputLevelRef.current = 0;
    setInputLevel(0);

    recording.setProgressUpdateInterval(STATUS_UPDATE_INTERVAL_MS);
    recording.setOnRecordingStatusUpdate((status) => {
      const nextDuration = Math.floor(status.durationMillis / 1000);
      setDuration((prev) => (prev === nextDuration ? prev : nextDuration));

      const rawLevel = normalizeInputLevel(status.metering);
      const previousLevel = inputLevelRef.current;
      const smoothing = rawLevel > previousLevel ? ATTACK_SMOOTHING : RELEASE_SMOOTHING;
      const smoothedLevel = previousLevel + (rawLevel - previousLevel) * smoothing;
      const nextLevel = smoothedLevel < 0.01 ? 0 : smoothedLevel;

      inputLevelRef.current = nextLevel;
      setInputLevel(nextLevel);
    });

    try {
      await startPreparedRecording(recording);
    } catch (error) {
      await recording.stopAndUnloadAsync().catch(() => {});
      throw error;
    }

    recordingRef.current = recording;
    setState('recording');
  }, []);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    const recording = recordingRef.current;
    if (!recording) return null;

    recording.setOnRecordingStatusUpdate(null);
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    recordingRef.current = null;
    inputLevelRef.current = 0;
    setInputLevel(0);
    setState('idle');

    return uri;
  }, []);

  return { state, duration, inputLevel, startRecording, stopRecording };
}
