import { useState, useRef, useCallback } from 'react';
import { Audio } from 'expo-av';

type RecorderState = 'idle' | 'recording';

export function useAudioRecorder() {
  const [state, setState] = useState<RecorderState>('idle');
  const [duration, setDuration] = useState(0);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
    await recording.startAsync();

    recordingRef.current = recording;
    setDuration(0);
    setState('recording');

    timerRef.current = setInterval(() => {
      setDuration((d) => d + 1);
    }, 1000);
  }, []);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    const recording = recordingRef.current;
    if (!recording) return null;

    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    recordingRef.current = null;
    setState('idle');

    return uri;
  }, []);

  return { state, duration, startRecording, stopRecording };
}
