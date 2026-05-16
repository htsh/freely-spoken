import { useState, useRef, useCallback, useEffect } from 'react';
import { Audio } from 'expo-av';

type RecorderState = 'idle' | 'recording';

const STATUS_UPDATE_INTERVAL_MS = 120;
const MIN_METER_DB = -60;
const NOISE_GATE = 0.06;
const ATTACK_SMOOTHING = 0.45;
const RELEASE_SMOOTHING = 0.18;

function normalizeInputLevel(metering?: number): number {
  if (typeof metering !== 'number' || Number.isNaN(metering)) return 0;

  const clampedDb = Math.max(MIN_METER_DB, Math.min(0, metering));
  const normalized = (clampedDb - MIN_METER_DB) / Math.abs(MIN_METER_DB);
  return normalized < NOISE_GATE ? 0 : normalized;
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

    await Audio.setAudioModeAsync({
      allowsRecordingIOS: true,
      playsInSilentModeIOS: true,
    });

    const recording = new Audio.Recording();
    await recording.prepareToRecordAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);

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

    await recording.startAsync();

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
