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
      // TODO: transcribe and analyze in next tasks
      console.log('Recorded audio at:', uri);
    }
  };

  const handleReset = () => {
    setAppState('idle');
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

        {appState === 'results' && (
          <View style={styles.center}>
            <ThemedText>Results will go here</ThemedText>
            <Pressable style={styles.resetButton} onPress={handleReset}>
              <ThemedText style={styles.resetText}>Record Again</ThemedText>
            </Pressable>
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
  resetButton: {
    marginTop: 24,
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    backgroundColor: '#333',
  },
  resetText: {
    color: '#fff',
    fontWeight: '600',
  },
});
