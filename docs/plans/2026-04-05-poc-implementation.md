# mic-check PoC Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Single-screen iOS app that records audio, transcribes it on-device, and extracts sentiment/emotions using Apple Foundation Models.

**Architecture:** Three-state single screen (idle → recording → results). Audio captured with `expo-av`, transcribed via `expo-speech-recognition` from the recorded file, then the transcript is fed to Apple's on-device LLM via `@ratley/react-native-apple-foundation-models` for structured sentiment extraction.

**Tech Stack:** Expo SDK 54, React Native 0.81, TypeScript, expo-av, expo-speech-recognition, @ratley/react-native-apple-foundation-models

---

### Task 1: Install dependencies and configure plugins

**Files:**
- Modify: `package.json`
- Modify: `app.json` (plugins array)

**Step 1: Install packages**

Run:
```bash
npx expo install expo-av
npm install expo-speech-recognition @ratley/react-native-apple-foundation-models
```

**Step 2: Add plugins to app.json**

Add to the `plugins` array in `app.json`:
```json
[
  "expo-av",
  {
    "microphonePermission": "Allow mic-check to access your microphone for voice recording."
  }
],
[
  "expo-speech-recognition",
  {
    "microphonePermission": "Allow mic-check to access your microphone.",
    "speechRecognitionPermission": "Allow mic-check to use speech recognition to transcribe your recordings."
  }
]
```

**Step 3: Commit**

```bash
git add package.json package-lock.json app.json
git commit -m "feat: add audio recording, speech recognition, and foundation models deps"
```

---

### Task 2: Strip the app down to a single screen

Remove the tabs layout and replace with a single screen. Keep the themed components — they're useful.

**Files:**
- Delete: `app/(tabs)/_layout.tsx`
- Delete: `app/(tabs)/index.tsx`
- Delete: `app/(tabs)/explore.tsx`
- Delete: `app/modal.tsx`
- Modify: `app/_layout.tsx` — simplify to single Stack screen
- Create: `app/index.tsx` — placeholder home screen

**Step 1: Delete tab files and modal**

```bash
rm -rf app/\(tabs\) app/modal.tsx
```

**Step 2: Simplify root layout**

Replace `app/_layout.tsx` with:

```tsx
import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import 'react-native-reanimated';

import { useColorScheme } from '@/hooks/use-color-scheme';

export default function RootLayout() {
  const colorScheme = useColorScheme();

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <Stack screenOptions={{ headerShown: false }} />
      <StatusBar style="auto" />
    </ThemeProvider>
  );
}
```

**Step 3: Create placeholder home screen**

Create `app/index.tsx`:

```tsx
import { StyleSheet, View } from 'react-native';
import { ThemedText } from '@/components/themed-text';

export default function HomeScreen() {
  return (
    <View style={styles.container}>
      <ThemedText type="title">mic-check</ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
```

**Step 4: Verify app loads**

Run:
```bash
npx expo start --ios
```

Confirm: single screen shows "mic-check" centered.

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: strip to single screen layout"
```

---

### Task 3: Build the recording UI and audio capture

Implement the idle and recording states with `expo-av`.

**Files:**
- Modify: `app/index.tsx` — full recording UI
- Create: `hooks/use-audio-recorder.ts` — recording logic hook

**Step 1: Create the recording hook**

Create `hooks/use-audio-recorder.ts`:

```tsx
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
```

**Step 2: Build the recording UI**

Replace `app/index.tsx`:

```tsx
import { useState } from 'react';
import { StyleSheet, View, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useAudioRecorder } from '@/hooks/use-audio-recorder';

type AppState = 'idle' | 'recording' | 'processing' | 'results';

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function HomeScreen() {
  const [appState, setAppState] = useState<AppState>('idle');
  const recorder = useAudioRecorder();

  const handleRecord = async () => {
    try {
      await recorder.startRecording();
      setAppState('recording');
    } catch (e) {
      console.error('Failed to start recording:', e);
    }
  };

  const handleStop = async () => {
    const uri = await recorder.stopRecording();
    if (uri) {
      setAppState('processing');
      // TODO: transcribe and analyze in Task 4 & 5
      console.log('Recorded audio at:', uri);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ThemedView style={styles.container}>
        <ThemedText type="title" style={styles.title}>mic-check</ThemedText>

        {appState === 'idle' && (
          <View style={styles.center}>
            <Pressable style={styles.recordButton} onPress={handleRecord}>
              <View style={styles.recordDot} />
            </Pressable>
            <ThemedText style={styles.hint}>Tap to record</ThemedText>
          </View>
        )}

        {appState === 'recording' && (
          <View style={styles.center}>
            <ThemedText style={styles.timer}>
              {formatDuration(recorder.duration)}
            </ThemedText>
            <Pressable style={styles.stopButton} onPress={handleStop}>
              <View style={styles.stopSquare} />
            </Pressable>
            <ThemedText style={styles.hint}>Recording...</ThemedText>
          </View>
        )}

        {appState === 'processing' && (
          <View style={styles.center}>
            <ThemedText>Processing...</ThemedText>
          </View>
        )}
      </ThemedView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
  },
  container: {
    flex: 1,
    paddingHorizontal: 24,
  },
  title: {
    textAlign: 'center',
    marginTop: 40,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    borderColor: '#ccc',
    justifyContent: 'center',
    alignItems: 'center',
  },
  recordDot: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#ff3b30',
  },
  stopButton: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    borderColor: '#ff3b30',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stopSquare: {
    width: 28,
    height: 28,
    borderRadius: 4,
    backgroundColor: '#ff3b30',
  },
  timer: {
    fontSize: 48,
    fontVariant: ['tabular-nums'],
    marginBottom: 24,
  },
  hint: {
    marginTop: 16,
    opacity: 0.6,
  },
});
```

**Step 3: Test on device**

Run: `npx expo run:ios` (need native build for microphone access)

Verify:
- Record button shows on launch
- Tapping it starts recording (timer counts up)
- Tapping stop returns to processing state
- Check console for recorded audio file URI

**Step 4: Commit**

```bash
git add app/index.tsx hooks/use-audio-recorder.ts
git commit -m "feat: add audio recording with idle/recording states"
```

---

### Task 4: Add transcription

Feed the recorded audio file to `expo-speech-recognition` for on-device transcription.

**Files:**
- Create: `hooks/use-transcriber.ts`
- Modify: `app/index.tsx` — wire up transcription after recording stops

**Step 1: Create the transcription hook**

Create `hooks/use-transcriber.ts`:

```tsx
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
```

**Step 2: Wire transcription into the main screen**

In `app/index.tsx`, add the transcriber hook and call it after recording stops:

```tsx
// Add import
import { useTranscriber } from '@/hooks/use-transcriber';

// Inside HomeScreen component, add:
const transcriber = useTranscriber();

// Modify handleStop:
const handleStop = async () => {
  const uri = await recorder.stopRecording();
  if (uri) {
    setAppState('processing');
    await transcriber.transcribe(uri);
  }
};

// Add useEffect to detect when transcription finishes:
// import { useEffect } from 'react';
useEffect(() => {
  if (appState === 'processing' && !transcriber.isTranscribing && transcriber.transcript) {
    setAppState('results');
  }
}, [appState, transcriber.isTranscribing, transcriber.transcript]);
```

Add a results state to the JSX (after the processing block):

```tsx
{appState === 'results' && (
  <View style={styles.results}>
    <ThemedText type="subtitle">Transcript</ThemedText>
    <ThemedText style={styles.transcript}>{transcriber.transcript}</ThemedText>

    {/* TODO: sentiment results go here (Task 5) */}

    <Pressable
      style={styles.resetButton}
      onPress={() => {
        transcriber.reset();
        setAppState('idle');
      }}>
      <ThemedText style={styles.resetText}>Record Again</ThemedText>
    </Pressable>
  </View>
)}
```

Add styles:

```tsx
results: {
  flex: 1,
  paddingTop: 40,
},
transcript: {
  marginTop: 8,
  marginBottom: 24,
  lineHeight: 22,
},
resetButton: {
  marginTop: 'auto',
  marginBottom: 40,
  paddingVertical: 16,
  alignItems: 'center',
  borderRadius: 12,
  backgroundColor: '#333',
},
resetText: {
  color: '#fff',
  fontWeight: '600',
},
```

**Step 3: Test on device**

Run: `npx expo run:ios`

Verify:
- Record something, tap stop
- "Processing..." shows briefly
- Transcript appears on results screen
- "Record Again" resets to idle

**Step 4: Commit**

```bash
git add hooks/use-transcriber.ts app/index.tsx
git commit -m "feat: add on-device speech transcription after recording"
```

---

### Task 5: Add sentiment extraction with Apple Foundation Models

Feed the transcript to the on-device LLM and extract structured sentiment data.

**Files:**
- Create: `hooks/use-sentiment-analyzer.ts`
- Modify: `app/index.tsx` — wire up analysis after transcription, display results

**Step 1: Create the sentiment analysis hook**

Create `hooks/use-sentiment-analyzer.ts`:

```tsx
import { useState, useCallback } from 'react';
import {
  generateObject,
  getTextModelAvailability,
} from '@ratley/react-native-apple-foundation-models';

const EMOTIONS = [
  'joy', 'sadness', 'anger', 'fear', 'surprise', 'disgust',
  'hope', 'anxiety', 'peace', 'love', 'gratitude', 'frustration',
  'excitement', 'confusion',
] as const;

const SENTIMENT_SCHEMA = {
  type: 'object' as const,
  required: ['sentiment', 'emotions', 'confidence'],
  properties: {
    sentiment: {
      type: 'string' as const,
    },
    emotions: {
      type: 'array' as const,
      items: { type: 'string' as const },
    },
    confidence: {
      type: 'number' as const,
      minimum: 0,
      maximum: 1,
    },
  },
};

export type SentimentResult = {
  sentiment: 'positive' | 'negative' | 'neutral';
  emotions: string[];
  confidence: number;
};

export function useSentimentAnalyzer() {
  const [result, setResult] = useState<SentimentResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = useCallback(async (text: string) => {
    setResult(null);
    setError(null);
    setIsAnalyzing(true);

    try {
      const availability = await getTextModelAvailability();
      if (availability.status !== 'available') {
        throw new Error(
          `Apple Intelligence not available: ${availability.reasonCode ?? 'unknown'}`
        );
      }

      const response = await generateObject({
        prompt: text,
        instructions: `You are a sentiment analyzer. Given text, classify its sentiment and emotions.

Return:
- sentiment: exactly one of "positive", "negative", or "neutral"
- emotions: an array of emotions present. Choose ONLY from: ${EMOTIONS.join(', ')}
- confidence: a number between 0 and 1 indicating how confident you are

Do NOT repeat or paraphrase any of the input text.`,
        schema: SENTIMENT_SCHEMA,
        temperature: 0.2,
      });

      setResult(response as SentimentResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setIsAnalyzing(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setIsAnalyzing(false);
  }, []);

  return { result, isAnalyzing, error, analyze, reset };
}
```

**Step 2: Wire analysis into the main screen**

In `app/index.tsx`:

```tsx
// Add import
import { useSentimentAnalyzer } from '@/hooks/use-sentiment-analyzer';

// Inside HomeScreen, add:
const analyzer = useSentimentAnalyzer();

// Update the useEffect to chain transcription → analysis:
useEffect(() => {
  if (appState === 'processing' && !transcriber.isTranscribing && transcriber.transcript) {
    analyzer.analyze(transcriber.transcript);
  }
}, [appState, transcriber.isTranscribing, transcriber.transcript]);

useEffect(() => {
  if (appState === 'processing' && !analyzer.isAnalyzing && analyzer.result) {
    setAppState('results');
  }
}, [appState, analyzer.isAnalyzing, analyzer.result]);

// Update the reset handler:
const handleReset = () => {
  transcriber.reset();
  analyzer.reset();
  setAppState('idle');
};
```

Update the results JSX to show sentiment:

```tsx
{appState === 'results' && (
  <View style={styles.results}>
    <ThemedText type="subtitle">Transcript</ThemedText>
    <ThemedText style={styles.transcript}>{transcriber.transcript}</ThemedText>

    {analyzer.result && (
      <>
        <ThemedText type="subtitle">Sentiment</ThemedText>
        <ThemedText style={styles.sentimentValue}>
          {analyzer.result.sentiment} ({Math.round(analyzer.result.confidence * 100)}%)
        </ThemedText>

        <ThemedText type="subtitle" style={styles.emotionsLabel}>Emotions</ThemedText>
        <View style={styles.emotionTags}>
          {analyzer.result.emotions.map((emotion) => (
            <View key={emotion} style={styles.tag}>
              <ThemedText style={styles.tagText}>{emotion}</ThemedText>
            </View>
          ))}
        </View>
      </>
    )}

    {analyzer.error && (
      <ThemedText style={styles.errorText}>{analyzer.error}</ThemedText>
    )}

    <Pressable style={styles.resetButton} onPress={handleReset}>
      <ThemedText style={styles.resetText}>Record Again</ThemedText>
    </Pressable>
  </View>
)}
```

Add styles:

```tsx
sentimentValue: {
  marginTop: 4,
  marginBottom: 16,
  fontSize: 18,
  textTransform: 'capitalize',
},
emotionsLabel: {
  marginTop: 8,
},
emotionTags: {
  flexDirection: 'row',
  flexWrap: 'wrap',
  gap: 8,
  marginTop: 8,
},
tag: {
  paddingHorizontal: 12,
  paddingVertical: 6,
  borderRadius: 16,
  backgroundColor: 'rgba(128, 128, 128, 0.2)',
},
tagText: {
  fontSize: 14,
},
errorText: {
  color: '#ff3b30',
  marginTop: 8,
},
```

**Step 3: Test on device**

Run: `npx expo run:ios`

Verify:
- Record a sentence like "I'm so happy today, everything is going great!"
- After recording stops, processing state shows
- Results show transcript, sentiment (positive), and emotion tags (joy, gratitude, etc.)
- "Record Again" resets everything

Also test:
- A negative statement: "This is terrible, I'm really frustrated"
- A neutral statement: "The meeting is at 3pm tomorrow"

**Step 4: Commit**

```bash
git add hooks/use-sentiment-analyzer.ts app/index.tsx
git commit -m "feat: add on-device sentiment extraction via Apple Foundation Models"
```

---

### Task 6: Handle error states and edge cases

**Files:**
- Modify: `app/index.tsx` — add error display and edge case handling

**Step 1: Add error state to the UI**

In `app/index.tsx`, handle:
- Transcription errors (show message, allow retry)
- Analysis errors / Apple Intelligence unavailable (show transcript without sentiment)
- Empty transcript (show "No speech detected", allow retry)

Add to the processing state JSX:

```tsx
{appState === 'processing' && (
  <View style={styles.center}>
    {transcriber.error ? (
      <>
        <ThemedText style={styles.errorText}>{transcriber.error}</ThemedText>
        <Pressable style={styles.resetButton} onPress={handleReset}>
          <ThemedText style={styles.resetText}>Try Again</ThemedText>
        </Pressable>
      </>
    ) : (
      <ThemedText>Processing...</ThemedText>
    )}
  </View>
)}
```

Update the transcription → analysis effect to handle empty transcript:

```tsx
useEffect(() => {
  if (appState === 'processing' && !transcriber.isTranscribing) {
    if (transcriber.transcript) {
      analyzer.analyze(transcriber.transcript);
    } else if (transcriber.error) {
      // Stay in processing to show error
    } else {
      // Empty transcript, no error — no speech detected
      setAppState('results');
    }
  }
}, [appState, transcriber.isTranscribing, transcriber.transcript, transcriber.error]);
```

In results, handle missing transcript:

```tsx
{!transcriber.transcript && (
  <ThemedText style={styles.hint}>No speech detected</ThemedText>
)}
```

**Step 2: Test edge cases**

- Record silence → should show "No speech detected"
- Record with airplane mode → should still work (on-device)
- Deny microphone permission → should show error

**Step 3: Commit**

```bash
git add app/index.tsx
git commit -m "feat: add error handling for transcription and analysis failures"
```

---

### Task 7: Clean up unused starter files

**Files:**
- Delete: `components/hello-wave.tsx`
- Delete: `components/parallax-scroll-view.tsx`
- Delete: `components/ui/collapsible.tsx`
- Delete: `app-example/` (if exists)
- Delete: `scripts/reset-project.js`

**Step 1: Remove unused files**

```bash
rm -f components/hello-wave.tsx components/parallax-scroll-view.tsx components/ui/collapsible.tsx scripts/reset-project.js
rm -rf app-example
```

**Step 2: Remove reset-project script from package.json**

Remove the `"reset-project"` line from `scripts` in `package.json`.

**Step 3: Verify app still builds**

```bash
npx expo run:ios
```

**Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove unused starter files"
```
