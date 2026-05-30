import { useState, useCallback } from 'react';
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from 'expo-speech-recognition';

export function useTranscriber() {
  const [transcript, setTranscript] = useState('');
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useSpeechRecognitionEvent('result', (event) => {
    const text = event.results[0]?.transcript ?? '';
    setTranscript(text);
  });

  useSpeechRecognitionEvent('end', () => {
    setIsTranscribing(false);
  });

  useSpeechRecognitionEvent('error', (event) => {
    setError(`${event.error}: ${event.message}`);
    setIsTranscribing(false);
  });

  const transcribe = useCallback(async (audioUri: string) => {
    setTranscript('');
    setError(null);
    setIsTranscribing(true);

    const { granted } = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
    if (!granted) {
      setError('Speech recognition permission not granted');
      setIsTranscribing(false);
      return;
    }

    ExpoSpeechRecognitionModule.start({
      lang: 'en-US',
      interimResults: false,
      requiresOnDeviceRecognition: true,
      audioSource: {
        uri: audioUri,
      },
    });
  }, []);

  const reset = useCallback(() => {
    setTranscript('');
    setError(null);
    setIsTranscribing(false);
  }, []);

  return { transcript, isTranscribing, error, transcribe, reset };
}
