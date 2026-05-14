import { useState, useEffect, useMemo } from 'react';
import { StyleSheet, View, Pressable, ScrollView } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useAudioRecorder } from '@/hooks/use-audio-recorder';
import { useTranscriber } from '@/hooks/use-transcriber';
import { useSentimentAnalyzer } from '@/hooks/use-sentiment-analyzer';
import { useSpiritualResponseLookup } from '@/hooks/use-spiritual-response-lookup';
import {
  AppVariant,
  ChristianLookupResult,
  LookupRequest,
  LookupResult,
  Reference,
  getBuildAppVariant,
  isStoicStub,
} from '@/services/lookup-client';

type AppState = 'idle' | 'recording' | 'processing' | 'responseLookup' | 'results';

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const PRIMARY_HEADINGS: Record<AppVariant, string> = {
  christian: 'A verse for you',
  stoic: 'A passage for you',
};

export default function HomeScreen() {
  const [appState, setAppState] = useState<AppState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [showAlternates, setShowAlternates] = useState(false);

  const appVariant = useMemo<AppVariant>(() => getBuildAppVariant(), []);

  const { duration, startRecording, stopRecording } = useAudioRecorder();
  const {
    transcript, isTranscribing, error: transcribeError,
    transcribe, reset: resetTranscriber,
  } = useTranscriber();
  const {
    result: sentimentResult, isAnalyzing, error: analyzerError,
    analyze, reset: resetAnalyzer,
  } = useSentimentAnalyzer();
  const {
    result: lookupResult, isLoading: isLookingUp, error: lookupError,
    lookup, reset: resetLookup,
  } = useSpiritualResponseLookup();

  const handleRecord = async () => {
    setError(null);
    try {
      await startRecording();
      setAppState('recording');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start recording');
    }
  };

  const handleStop = async () => {
    try {
      const uri = await stopRecording();
      if (!uri) {
        setError('No audio was captured');
        setAppState('idle');
        return;
      }
      setAppState('processing');
      await transcribe(uri);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to stop recording');
      setAppState('idle');
    }
  };

  const handleReset = () => {
    resetTranscriber();
    resetAnalyzer();
    resetLookup();
    setError(null);
    setShowAlternates(false);
    setAppState('idle');
  };

  const buildLookupRequest = (): LookupRequest | null => {
    if (!sentimentResult) return null;
    return {
      appVariant,
      anonymizedText: sentimentResult.anonymizedText,
      sentiment: sentimentResult.sentiment,
      emotions: sentimentResult.emotions,
      confidence: sentimentResult.confidence,
    };
  };

  const handleRetryLookup = () => {
    const req = buildLookupRequest();
    if (req) lookup(req);
  };

  // processing → start sentiment analysis when transcript arrives.
  useEffect(() => {
    if (appState !== 'processing' || isTranscribing) return;

    if (transcript) {
      analyze(transcript);
    } else {
      // Empty transcript or transcription error — skip lookup, go to results.
      setAppState('results');
    }
  }, [appState, isTranscribing, transcript, transcribeError, analyze]);

  // processing → responseLookup once sentiment finishes (success only).
  useEffect(() => {
    if (appState !== 'processing' || isAnalyzing) return;

    if (sentimentResult) {
      setAppState('responseLookup');
      lookup({
        appVariant,
        anonymizedText: sentimentResult.anonymizedText,
        sentiment: sentimentResult.sentiment,
        emotions: sentimentResult.emotions,
        confidence: sentimentResult.confidence,
      });
    } else if (analyzerError) {
      // Sentiment failed — skip lookup, render the analyzer error.
      setAppState('results');
    }
  }, [appState, isAnalyzing, sentimentResult, analyzerError, appVariant, lookup]);

  // responseLookup → results when lookup settles (success or error).
  useEffect(() => {
    if (appState !== 'responseLookup' || isLookingUp) return;
    if (lookupResult || lookupError) {
      setAppState('results');
    }
  }, [appState, isLookingUp, lookupResult, lookupError]);

  const processingLabel = isTranscribing
    ? 'Transcribing...'
    : isAnalyzing
      ? 'Analyzing sentiment and privacy...'
      : 'Processing...';

  return (
    <SafeAreaView style={styles.safeArea}>
      <ThemedView style={styles.container}>
        <ThemedText type="title" style={styles.title}>mic-check</ThemedText>

        {__DEV__ && (
          <Pressable
            style={styles.debugLink}
            onPress={() => router.push('/debug')}
            hitSlop={8}
          >
            <ThemedText style={styles.debugLinkText}>Debug → sentiment + privacy</ThemedText>
          </Pressable>
        )}

        {appState === 'idle' && (
          <View style={styles.center}>
            <Pressable style={styles.recordButton} onPress={handleRecord}>
              <View style={styles.recordDot} />
            </Pressable>
            <ThemedText style={styles.hint}>Tap to record</ThemedText>
            {error && (
              <ThemedText style={styles.errorText}>{error}</ThemedText>
            )}
          </View>
        )}

        {appState === 'recording' && (
          <View style={styles.center}>
            <ThemedText style={styles.timer}>
              {formatDuration(duration)}
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

        {appState === 'responseLookup' && (
          <View style={styles.center}>
            <ThemedText>Finding a response...</ThemedText>
          </View>
        )}

        {appState === 'results' && (
          <ScrollView style={styles.results} contentContainerStyle={styles.resultsContent}>
            {lookupResult ? (
              <LookupResultBlock
                result={lookupResult}
                appVariant={appVariant}
                showAlternates={showAlternates}
                onToggleAlternates={() => setShowAlternates((v) => !v)}
              />
            ) : lookupError ? (
              <ThemedView style={styles.lookupErrorBlock}>
                <ThemedText style={styles.errorText}>{lookupError}</ThemedText>
                <Pressable style={styles.retryButton} onPress={handleRetryLookup}>
                  <ThemedText style={styles.retryText}>Try again</ThemedText>
                </Pressable>
              </ThemedView>
            ) : null}

            {transcript ? (
              <>
                <ThemedText type="subtitle" style={styles.sectionHeading}>Transcript</ThemedText>
                <ThemedText style={styles.transcript}>{transcript}</ThemedText>
              </>
            ) : (
              <ThemedText style={styles.hint}>No speech detected</ThemedText>
            )}

            {transcribeError && (
              <ThemedText style={styles.errorText}>{transcribeError}</ThemedText>
            )}

            {sentimentResult && (
              <>
                <ThemedText type="subtitle" style={styles.sectionHeading}>
                  Sentiment JSON
                </ThemedText>
                <View style={styles.jsonBlock}>
                  <ThemedText style={styles.jsonText}>
                    {JSON.stringify(
                      {
                        sentiment: sentimentResult.sentiment,
                        emotions: sentimentResult.emotions,
                        confidence: sentimentResult.confidence,
                      },
                      null,
                      2,
                    )}
                  </ThemedText>
                </View>

                <ThemedText type="subtitle" style={styles.anonymousLabel}>
                  Guarded anonymous version
                </ThemedText>
                <ThemedText style={styles.anonymousText}>
                  {sentimentResult.anonymizedText}
                </ThemedText>
              </>
            )}

            {analyzerError && (
              <ThemedText style={styles.errorText}>{analyzerError}</ThemedText>
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

type LookupResultBlockProps = {
  result: LookupResult;
  appVariant: AppVariant;
  showAlternates: boolean;
  onToggleAlternates: () => void;
};

function LookupResultBlock({
  result,
  appVariant,
  showAlternates,
  onToggleAlternates,
}: LookupResultBlockProps) {
  if (isStoicStub(result)) {
    return (
      <ThemedView style={styles.stoicStubBlock}>
        <ThemedText type="subtitle">Stoic mode (not yet implemented)</ThemedText>
        <ThemedText style={styles.stoicStubText}>{result.message}</ThemedText>
        {result.crisisFlag && <CrisisBanner />}
      </ThemedView>
    );
  }

  return (
    <View>
      {result.crisisFlag && <CrisisBanner />}

      <ThemedText type="subtitle" style={styles.primaryHeading}>
        {PRIMARY_HEADINGS[appVariant]}
      </ThemedText>

      <ReferenceBlock reference={result.primary} variant="primary" />

      <Pressable style={styles.altToggle} onPress={onToggleAlternates}>
        <ThemedText style={styles.altToggleText}>
          {showAlternates ? 'Hide alternates' : `Show ${result.alternates.length} alternates`}
        </ThemedText>
      </Pressable>

      {showAlternates && (
        <View style={styles.alternatesBlock}>
          {result.alternates.map((ref, i) => (
            <ReferenceBlock key={`${ref.ref}-${i}`} reference={ref} variant="alternate" />
          ))}
        </View>
      )}

      <ProviderBadge result={result} />
    </View>
  );
}

function ReferenceBlock({
  reference,
  variant,
}: {
  reference: Reference;
  variant: 'primary' | 'alternate';
}) {
  const isPrimary = variant === 'primary';
  return (
    <ThemedView style={isPrimary ? styles.primaryRefBlock : styles.alternateRefBlock}>
      <ThemedText style={isPrimary ? styles.refLabel : styles.altRefLabel}>
        {reference.ref}
      </ThemedText>

      {reference.text ? (
        <>
          <ThemedText style={isPrimary ? styles.verseText : styles.altVerseText}>
            {reference.text}
          </ThemedText>
          {reference.translation && (
            <ThemedText style={styles.translationLabel}>{reference.translation}</ThemedText>
          )}
        </>
      ) : (
        <ThemedText style={styles.textErrorLabel}>
          Couldn’t fetch the canonical text for this reference.
        </ThemedText>
      )}

      <ThemedText style={styles.shortReason}>{reference.shortReason}</ThemedText>
    </ThemedView>
  );
}

function ProviderBadge({ result }: { result: ChristianLookupResult }) {
  return (
    <ThemedText style={styles.providerBadge}>
      {result.provider} · {result.model}
      {result.fallbackUsed ? ' · fallback' : ''}
      {result.retryCount > 0 ? ` · ${result.retryCount} retries` : ''}
    </ThemedText>
  );
}

function CrisisBanner() {
  return (
    <ThemedView style={styles.crisisBanner}>
      <ThemedText style={styles.crisisBannerText}>
        It sounds like you might be going through something serious. If you’re in danger, call your local emergency number. In the US you can also reach the 988 Suicide & Crisis Lifeline.
      </ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1, paddingHorizontal: 24 },
  title: { textAlign: 'center', marginTop: 40 },
  debugLink: {
    alignSelf: 'center',
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(10,126,164,0.15)',
  },
  debugLinkText: { fontSize: 12, opacity: 0.8 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  recordButton: {
    width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: '#ccc',
    justifyContent: 'center', alignItems: 'center',
  },
  recordDot: { width: 32, height: 32, borderRadius: 16, backgroundColor: '#ff3b30' },
  stopButton: {
    width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: '#ff3b30',
    justifyContent: 'center', alignItems: 'center',
  },
  stopSquare: { width: 28, height: 28, borderRadius: 4, backgroundColor: '#ff3b30' },
  timer: { fontSize: 48, lineHeight: 56, fontVariant: ['tabular-nums'], marginBottom: 24 },
  hint: { marginTop: 16, opacity: 0.6 },
  results: { flex: 1, marginTop: 24 },
  resultsContent: { paddingBottom: 40 },
  sectionHeading: { marginTop: 24 },
  transcript: { marginTop: 8, marginBottom: 24, lineHeight: 22 },
  jsonBlock: {
    marginTop: 8, padding: 12, borderRadius: 8, backgroundColor: 'rgba(0,0,0,0.06)',
  },
  jsonText: { fontFamily: 'ui-monospace', fontSize: 13, lineHeight: 18 },
  anonymousLabel: { marginTop: 24 },
  anonymousText: { marginTop: 8, lineHeight: 22 },
  errorText: { color: '#ff3b30', marginTop: 8, marginBottom: 16 },
  resetButton: {
    marginTop: 32, paddingVertical: 16, alignItems: 'center', borderRadius: 12,
    backgroundColor: '#333',
  },
  resetText: { color: '#fff', fontWeight: '600' },

  primaryHeading: { marginTop: 8 },
  primaryRefBlock: {
    marginTop: 12,
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(10,126,164,0.08)',
  },
  alternateRefBlock: {
    marginTop: 12,
    padding: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  refLabel: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  altRefLabel: { fontSize: 15, fontWeight: '600', marginBottom: 6 },
  verseText: { fontSize: 17, lineHeight: 26 },
  altVerseText: { fontSize: 15, lineHeight: 22 },
  translationLabel: { marginTop: 6, fontSize: 12, opacity: 0.7 },
  textErrorLabel: { marginTop: 4, opacity: 0.6, fontStyle: 'italic' },
  shortReason: { marginTop: 12, fontSize: 14, lineHeight: 20, opacity: 0.85 },
  altToggle: {
    marginTop: 16,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  altToggleText: { fontSize: 13 },
  alternatesBlock: { marginTop: 4 },
  providerBadge: { marginTop: 16, fontSize: 11, opacity: 0.5 },
  crisisBanner: {
    marginTop: 12,
    padding: 14,
    borderRadius: 10,
    backgroundColor: 'rgba(255,59,48,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255,59,48,0.4)',
  },
  crisisBannerText: { lineHeight: 20 },
  stoicStubBlock: {
    marginTop: 12,
    padding: 16,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.05)',
  },
  stoicStubText: { marginTop: 8, lineHeight: 22 },
  lookupErrorBlock: { marginTop: 12 },
  retryButton: {
    alignSelf: 'flex-start',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    backgroundColor: '#333',
  },
  retryText: { color: '#fff', fontWeight: '600' },
});
