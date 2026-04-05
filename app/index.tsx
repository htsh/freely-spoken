import { useState, useEffect } from 'react';
import { StyleSheet, View, Pressable, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useAudioRecorder } from '@/hooks/use-audio-recorder';
import { useTranscriber } from '@/hooks/use-transcriber';
import { useSentimentAnalyzer } from '@/hooks/use-sentiment-analyzer';

type AppState = 'idle' | 'recording' | 'processing' | 'results';

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function HomeScreen() {
  const [appState, setAppState] = useState<AppState>('idle');
  const recorder = useAudioRecorder();
  const transcriber = useTranscriber();
  const analyzer = useSentimentAnalyzer();

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
      await transcriber.transcribe(uri);
    }
  };

  const handleReset = () => {
    transcriber.reset();
    analyzer.reset();
    setAppState('idle');
  };

  // Chain: transcription done → start analysis
  useEffect(() => {
    if (appState === 'processing' && !transcriber.isTranscribing) {
      if (transcriber.transcript) {
        analyzer.analyze(transcriber.transcript);
      } else if (transcriber.error) {
        setAppState('results');
      }
    }
  }, [appState, transcriber.isTranscribing, transcriber.transcript, transcriber.error]);

  // Chain: analysis done → show results
  useEffect(() => {
    if (appState === 'processing' && !analyzer.isAnalyzing && (analyzer.result || analyzer.error)) {
      setAppState('results');
    }
  }, [appState, analyzer.isAnalyzing, analyzer.result, analyzer.error]);

  const processingLabel = transcriber.isTranscribing
    ? 'Transcribing...'
    : analyzer.isAnalyzing
      ? 'Analyzing sentiment...'
      : 'Processing...';

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
            <ThemedText>{processingLabel}</ThemedText>
          </View>
        )}

        {appState === 'results' && (
          <ScrollView style={styles.results} contentContainerStyle={styles.resultsContent}>
            {transcriber.transcript ? (
              <>
                <ThemedText type="subtitle">Transcript</ThemedText>
                <ThemedText style={styles.transcript}>{transcriber.transcript}</ThemedText>
              </>
            ) : (
              <ThemedText style={styles.hint}>No speech detected</ThemedText>
            )}

            {transcriber.error && (
              <ThemedText style={styles.errorText}>{transcriber.error}</ThemedText>
            )}

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
          </ScrollView>
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
  results: {
    flex: 1,
    marginTop: 24,
  },
  resultsContent: {
    paddingBottom: 40,
  },
  transcript: {
    marginTop: 8,
    marginBottom: 24,
    lineHeight: 22,
  },
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
    marginBottom: 16,
  },
  resetButton: {
    marginTop: 32,
    paddingVertical: 16,
    alignItems: 'center',
    borderRadius: 12,
    backgroundColor: '#333',
  },
  resetText: {
    color: '#fff',
    fontWeight: '600',
  },
});
