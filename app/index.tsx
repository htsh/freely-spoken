import { useState, useEffect, useMemo, useRef } from 'react';
import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import { StyleSheet, View, Pressable, ScrollView, Animated, Easing, AccessibilityInfo } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { getBrand } from '@/constants/brand';
import { Fonts } from '@/constants/theme';
import { useAudioRecorder } from '@/hooks/use-audio-recorder';
import { emptyHistory, pushSample } from '@/hooks/waveform-utils';
import type { SentimentResult } from '@/hooks/sentiment-utils';
import { useTranscriber } from '@/hooks/use-transcriber';
import { useSentimentAnalyzer } from '@/hooks/use-sentiment-analyzer';
import { useSpiritualResponseLookup } from '@/hooks/use-spiritual-response-lookup';
import {
  AppVariant,
  LookupRequest,
  LookupResult,
  Reference,
  ReferenceLookupResult,
  buildLookupRequest,
  getBuildAppVariant,
  isLookupUnavailable,
  isStoicStub,
} from '@/services/lookup-client';

type AppState = 'idle' | 'recording' | 'processing' | 'review' | 'responseLookup' | 'results';

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const PRIMARY_HEADINGS: Record<AppVariant, string> = {
  christian: 'A verse for you',
  stoic: 'A passage for you',
  dhammapada: 'A passage for you',
};

const LOOKUP_CTA_LABELS: Record<AppVariant, string> = {
  christian: 'Find My Verse',
  stoic: 'Find My Passage',
  dhammapada: 'Find My Passage',
};

const RESPONSE_NOUN_LABELS: Record<AppVariant, string> = {
  christian: 'verse',
  stoic: 'passage',
  dhammapada: 'passage',
};

const WAVEFORM_BAR_COUNT = 28;
const KEEP_AWAKE_TAG = 'recording-flow';
const WAVEFORM_BAR_MIN_HEIGHT = 4;
const WAVEFORM_BAR_HEIGHT_RANGE = 22;

type HomeStyles = ReturnType<typeof buildStyles>;

// React Native accepts 8-digit hex (#RRGGBBAA) on current iOS/Android. Used to
// derive translucent surfaces from the active variant's solid brand colors.
function withAlpha(hex: string, alpha: number): string {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return hex;
  const value = Math.round(alpha * 255).toString(16).padStart(2, '0');
  return `#${normalized}${value}`;
}

function RecordingLevelMeter({
  inputLevel,
  reduceMotion,
  styles,
}: {
  inputLevel: number;
  reduceMotion: boolean;
  styles: HomeStyles;
}) {
  const [history, setHistory] = useState<number[]>(() => emptyHistory(WAVEFORM_BAR_COUNT));

  useEffect(() => {
    if (reduceMotion) return;
    setHistory((prev) => pushSample(prev, inputLevel, WAVEFORM_BAR_COUNT));
  }, [inputLevel, reduceMotion]);

  // Reduce-motion: a calm, non-scrolling row — every bar reflects the current
  // level only (height changes in place, no horizontal movement).
  const levels = reduceMotion
    ? new Array(WAVEFORM_BAR_COUNT).fill(Math.max(0, Math.min(1, inputLevel)))
    : history;

  return (
    <View
      style={styles.levelMeter}
      accessible
      accessibilityRole="image"
      accessibilityLabel="Live microphone input level"
    >
      {levels.map((level, index) => (
        <View
          key={`meter-bar-${index}`}
          style={[
            styles.levelMeterBar,
            { height: WAVEFORM_BAR_MIN_HEIGHT + level * WAVEFORM_BAR_HEIGHT_RANGE },
          ]}
        />
      ))}
    </View>
  );
}

export default function HomeScreen() {
  const [appState, setAppState] = useState<AppState>('idle');
  const [error, setError] = useState<string | null>(null);
  const [showAlternates, setShowAlternates] = useState(false);
  const [reduceMotionEnabled, setReduceMotionEnabled] = useState(false);
  const pulseScale = useRef(new Animated.Value(1)).current;

  const appVariant = useMemo<AppVariant>(() => getBuildAppVariant(), []);
  const brand = useMemo(() => getBrand(appVariant), [appVariant]);
  const styles = useMemo(() => buildStyles(brand.colors), [brand.colors]);

  const {
    duration, inputLevel, startRecording, stopRecording,
  } = useAudioRecorder();
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

  const makeLookupRequest = (): LookupRequest | null => {
    if (!sentimentResult) return null;
    return buildLookupRequest(appVariant, sentimentResult);
  };

  const handleRetryLookup = () => {
    const req = makeLookupRequest();
    if (req) lookup(req);
  };

  const handleSubmitLookup = () => {
    const req = makeLookupRequest();
    if (!req) {
      setError('No private summary was created');
      return;
    }

    setError(null);
    setAppState('responseLookup');
    lookup(req);
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

  // processing → review once anonymization finishes (success only).
  useEffect(() => {
    if (appState !== 'processing' || isAnalyzing) return;

    if (sentimentResult) {
      setAppState('review');
    } else if (analyzerError) {
      // Sentiment failed — skip lookup, render the analyzer error.
      setAppState('results');
    }
  }, [appState, isAnalyzing, sentimentResult, analyzerError]);

  // responseLookup → results when lookup settles (success or error).
  useEffect(() => {
    if (appState !== 'responseLookup' || isLookingUp) return;
    if (lookupResult || lookupError) {
      setAppState('results');
    }
  }, [appState, isLookingUp, lookupResult, lookupError]);

  // Keep the screen awake while the user is actively recording or waiting for
  // on-device processing / server lookup to complete.
  useEffect(() => {
    const working =
      appState === 'recording' ||
      appState === 'processing' ||
      appState === 'responseLookup';
    if (!working) return;

    activateKeepAwakeAsync(KEEP_AWAKE_TAG);
    return () => {
      deactivateKeepAwake(KEEP_AWAKE_TAG);
    };
  }, [appState]);

  useEffect(() => {
    let isMounted = true;

    AccessibilityInfo.isReduceMotionEnabled()
      .then((enabled) => {
        if (isMounted) setReduceMotionEnabled(enabled);
      })
      .catch(() => {});

    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setReduceMotionEnabled,
    );

    return () => {
      isMounted = false;
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    if (appState !== 'recording' || reduceMotionEnabled) {
      pulseScale.stopAnimation();
      pulseScale.setValue(1);
      return;
    }

    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseScale, {
          toValue: 1.08,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseScale, {
          toValue: 1,
          duration: 900,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    pulseAnimation.start();

    return () => {
      pulseAnimation.stop();
      pulseScale.stopAnimation();
      pulseScale.setValue(1);
    };
  }, [appState, reduceMotionEnabled, pulseScale]);

  const processingLabel = isTranscribing
    ? 'Transcribing on device...'
    : isAnalyzing
      ? 'Removing identifying details...'
      : 'Preparing private summary...';

  return (
    <SafeAreaView style={styles.safeArea}>
      <ThemedView style={styles.container}>
        <ThemedText type="title" style={styles.title}>{brand.wordmark}</ThemedText>

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
            <View style={styles.recordingControlWrap}>
              {!reduceMotionEnabled && (
                <Animated.View
                  pointerEvents="none"
                  style={[
                    styles.stopPulseHalo,
                    {
                      transform: [{ scale: pulseScale }],
                    },
                  ]}
                />
              )}
              <Pressable style={styles.stopButton} onPress={handleStop}>
                <View style={styles.stopSquare} />
              </Pressable>
            </View>
            <RecordingLevelMeter inputLevel={inputLevel} reduceMotion={reduceMotionEnabled} styles={styles} />
            <ThemedText style={styles.hint}>Recording...</ThemedText>
          </View>
        )}

        {appState === 'processing' && (
          <View style={styles.center}>
            <PrivateProcessingCue
              currentLabel={processingLabel}
              hasTranscript={Boolean(transcript)}
              isAnalyzing={isAnalyzing}
              isTranscribing={isTranscribing}
              styles={styles}
            />
          </View>
        )}

        {appState === 'review' && sentimentResult && (
          <PrivateSummaryReview
            appVariant={appVariant}
            result={sentimentResult}
            onFindResponse={handleSubmitLookup}
            onRecordAgain={handleReset}
            styles={styles}
          />
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
                styles={styles}
              />
            ) : lookupError ? (
              <ThemedView style={styles.lookupErrorBlock}>
                <ThemedText style={styles.errorText}>{lookupError}</ThemedText>
                <Pressable style={styles.retryButton} onPress={handleRetryLookup}>
                  <ThemedText style={styles.retryText}>Try again</ThemedText>
                </Pressable>
              </ThemedView>
            ) : null}

            {__DEV__ && transcript && (
              <>
                <ThemedText type="subtitle" style={styles.sectionHeading}>Transcript</ThemedText>
                <ThemedText style={styles.transcript}>{transcript}</ThemedText>
              </>
            )}

            {!transcript && !lookupResult && !lookupError && (
              <ThemedText style={styles.hint}>No speech detected</ThemedText>
            )}

            {transcribeError && (
              <ThemedText style={styles.errorText}>{transcribeError}</ThemedText>
            )}

            {__DEV__ && sentimentResult && (
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

function PrivateProcessingCue({
  currentLabel,
  hasTranscript,
  isAnalyzing,
  isTranscribing,
  styles,
}: {
  currentLabel: string;
  hasTranscript: boolean;
  isAnalyzing: boolean;
  isTranscribing: boolean;
  styles: HomeStyles;
}) {
  const steps = [
    {
      label: 'Transcribing on device',
      status: isTranscribing ? 'active' : hasTranscript ? 'done' : 'pending',
    },
    {
      label: 'Removing identifying details',
      status: isAnalyzing ? 'active' : 'pending',
    },
    {
      label: 'Preparing private summary',
      status: !isTranscribing && !isAnalyzing ? 'active' : 'pending',
    },
  ] as const;

  return (
    <View style={styles.processingPanel}>
      <View style={styles.processingHalo}>
        <View style={styles.processingCore} />
      </View>
      <ThemedText type="subtitle" style={styles.processingTitle}>
        {currentLabel}
      </ThemedText>
      <ThemedText style={styles.processingPrivacyText}>
        Your audio and raw transcript stay on this device.
      </ThemedText>

      <View style={styles.processingSteps}>
        {steps.map((step) => (
          <View key={step.label} style={styles.processingStep}>
            <View
              style={[
                styles.processingStepDot,
                step.status === 'active' ? styles.processingStepDotActive : undefined,
                step.status === 'done' ? styles.processingStepDotDone : undefined,
              ]}
            />
            <ThemedText
              style={[
                styles.processingStepText,
                step.status === 'pending' ? styles.processingStepTextPending : undefined,
              ]}
            >
              {step.label}
            </ThemedText>
          </View>
        ))}
      </View>
    </View>
  );
}

function PrivateSummaryReview({
  appVariant,
  result,
  onFindResponse,
  onRecordAgain,
  styles,
}: {
  appVariant: AppVariant;
  result: SentimentResult;
  onFindResponse: () => void;
  onRecordAgain: () => void;
  styles: HomeStyles;
}) {
  const emotionText = result.emotions.length > 0
    ? result.emotions.join(', ')
    : 'none detected';
  const responseNoun = RESPONSE_NOUN_LABELS[appVariant];

  return (
    <ScrollView style={styles.results} contentContainerStyle={styles.reviewContent}>
      <ThemedText type="subtitle" style={styles.reviewEyebrow}>
        This is what leaves your device
      </ThemedText>
      <ThemedText style={styles.reviewIntro}>
        Your audio and raw transcript stay on this device. Only this anonymized summary and
        general emotional metadata are sent to find a {responseNoun}.
      </ThemedText>

      <ThemedView style={styles.reviewPayloadBlock}>
        <ThemedText style={styles.reviewPayloadLabel}>Anonymized summary</ThemedText>
        <ThemedText style={styles.reviewPayloadText}>
          {result.anonymizedText}
        </ThemedText>
      </ThemedView>

      <View style={styles.reviewMetadataBlock}>
        <ThemedText style={styles.reviewMetadataTitle}>Details sent with summary</ThemedText>
        <View style={styles.reviewMetadataRow}>
          <ThemedText style={styles.reviewMetadataLabel}>Sentiment</ThemedText>
          <ThemedText style={styles.reviewMetadataValue}>{result.sentiment}</ThemedText>
        </View>
        <View style={styles.reviewMetadataRow}>
          <ThemedText style={styles.reviewMetadataLabel}>Emotions</ThemedText>
          <ThemedText style={styles.reviewMetadataValue}>{emotionText}</ThemedText>
        </View>
        <View style={styles.reviewMetadataRow}>
          <ThemedText style={styles.reviewMetadataLabel}>Confidence</ThemedText>
          <ThemedText style={styles.reviewMetadataValue}>
            {Math.round(result.confidence * 100)}
            %
          </ThemedText>
        </View>
      </View>

      <Pressable style={styles.findVerseButton} onPress={onFindResponse}>
        <ThemedText style={styles.findVerseText}>
          {LOOKUP_CTA_LABELS[appVariant]}
        </ThemedText>
      </Pressable>

      <Pressable style={styles.reviewSecondaryButton} onPress={onRecordAgain}>
        <ThemedText style={styles.reviewSecondaryText}>Record Again</ThemedText>
      </Pressable>
    </ScrollView>
  );
}

type LookupResultBlockProps = {
  result: LookupResult;
  appVariant: AppVariant;
  showAlternates: boolean;
  onToggleAlternates: () => void;
  styles: HomeStyles;
};

function LookupResultBlock({
  result,
  appVariant,
  showAlternates,
  onToggleAlternates,
  styles,
}: LookupResultBlockProps) {
  if (isStoicStub(result)) {
    return (
      <ThemedView style={styles.stoicStubBlock}>
        <ThemedText type="subtitle">Stoic mode (not yet implemented)</ThemedText>
        <ThemedText style={styles.stoicStubText}>{result.message}</ThemedText>
        {result.crisisFlag && <CrisisBanner styles={styles} />}
      </ThemedView>
    );
  }

  if (isLookupUnavailable(result)) {
    // Crisis hard-exclusion left too few eligible passages. Gentle empty state,
    // not an error — lead with support if the crisis flag is set.
    return (
      <ThemedView style={styles.unavailableBlock}>
        {result.crisisFlag && <CrisisBanner styles={styles} />}
        <ThemedText type="subtitle" style={styles.unavailableTitle}>
          No passage right now
        </ThemedText>
        <ThemedText style={styles.unavailableText}>{result.message}</ThemedText>
      </ThemedView>
    );
  }

  return (
    <View>
      {result.crisisFlag && <CrisisBanner styles={styles} />}

      <ThemedText type="subtitle" style={styles.primaryHeading}>
        {PRIMARY_HEADINGS[appVariant]}
      </ThemedText>

      <ReferenceBlock reference={result.primary} variant="primary" styles={styles} />

      <Pressable style={styles.altToggle} onPress={onToggleAlternates}>
        <ThemedText style={styles.altToggleText}>
          {showAlternates ? 'Hide alternates' : `Show ${result.alternates.length} alternates`}
        </ThemedText>
      </Pressable>

      {showAlternates && (
        <View style={styles.alternatesBlock}>
          {result.alternates.map((ref, i) => (
            <ReferenceBlock key={`${ref.ref}-${i}`} reference={ref} variant="alternate" styles={styles} />
          ))}
        </View>
      )}

      {__DEV__ && <ProviderBadge result={result} styles={styles} />}
    </View>
  );
}

function ReferenceBlock({
  reference,
  variant,
  styles,
}: {
  reference: Reference;
  variant: 'primary' | 'alternate';
  styles: HomeStyles;
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

function ProviderBadge({ result, styles }: { result: ReferenceLookupResult; styles: HomeStyles }) {
  return (
    <ThemedText style={styles.providerBadge}>
      {result.provider} · {result.model}
      {result.fallbackUsed ? ' · fallback' : ''}
      {result.retryCount > 0 ? ` · ${result.retryCount} retries` : ''}
    </ThemedText>
  );
}

function CrisisBanner({ styles }: { styles: HomeStyles }) {
  return (
    <ThemedView style={styles.crisisBanner}>
      <ThemedText style={styles.crisisBannerText}>
        It sounds like you might be going through something serious. If you’re in danger, call your local emergency number. In the US you can also reach the 988 Suicide & Crisis Lifeline.
      </ThemedText>
    </ThemedView>
  );
}

function buildStyles(colors: ReturnType<typeof getBrand>['colors']) {
  return StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1, paddingHorizontal: 24 },
  title: { textAlign: 'center', marginTop: 40 },
  debugLink: {
    alignSelf: 'center',
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: withAlpha(colors.accent, 0.16),
  },
  debugLinkText: { fontSize: 12, opacity: 0.8 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  recordButton: {
    width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: colors.surface,
    justifyContent: 'center', alignItems: 'center',
  },
  recordDot: { width: 32, height: 32, borderRadius: 16, backgroundColor: colors.destructive },
  recordingControlWrap: {
    width: 96,
    height: 96,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopPulseHalo: {
    position: 'absolute',
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: withAlpha(colors.destructive, 0.14),
  },
  stopButton: {
    width: 80, height: 80, borderRadius: 40, borderWidth: 4, borderColor: colors.destructive,
    justifyContent: 'center', alignItems: 'center',
  },
  stopSquare: { width: 28, height: 28, borderRadius: 4, backgroundColor: colors.destructive },
  levelMeter: {
    marginTop: 14,
    height: 30,
    flexDirection: 'row',
    alignItems: 'flex-end',
  },
  levelMeterBar: {
    width: 3,
    borderRadius: 2,
    marginHorizontal: 1,
    backgroundColor: colors.destructive,
  },
  timer: { fontSize: 48, lineHeight: 56, fontVariant: ['tabular-nums'], marginBottom: 24 },
  hint: { marginTop: 16, opacity: 0.6 },
  processingPanel: {
    width: '100%',
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  processingHalo: {
    width: 104,
    height: 104,
    borderRadius: 52,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: withAlpha(colors.accent, 0.12),
    borderWidth: 1,
    borderColor: withAlpha(colors.accent, 0.24),
  },
  processingCore: {
    width: 54,
    height: 54,
    borderRadius: 27,
    borderWidth: 5,
    borderColor: colors.primary,
    borderTopColor: colors.accent,
  },
  processingTitle: {
    marginTop: 22,
    textAlign: 'center',
  },
  processingPrivacyText: {
    marginTop: 8,
    maxWidth: 280,
    textAlign: 'center',
    lineHeight: 21,
    opacity: 0.72,
  },
  processingSteps: {
    width: '100%',
    marginTop: 28,
    paddingHorizontal: 18,
    paddingVertical: 16,
    borderRadius: 12,
    backgroundColor: colors.softSurface,
  },
  processingStep: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 7,
  },
  processingStepDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 10,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.28),
  },
  processingStepDotActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  processingStepDotDone: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  processingStepText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
  processingStepTextPending: {
    opacity: 0.52,
  },
  results: { flex: 1, marginTop: 24 },
  resultsContent: { paddingBottom: 40 },
  reviewContent: {
    paddingTop: 52,
    paddingBottom: 40,
  },
  reviewEyebrow: {
    marginTop: 4,
  },
  reviewIntro: {
    marginTop: 10,
    lineHeight: 22,
    opacity: 0.74,
  },
  reviewPayloadBlock: {
    marginTop: 24,
    padding: 16,
    borderRadius: 12,
    backgroundColor: withAlpha(colors.accent, 0.12),
    borderWidth: 1,
    borderColor: withAlpha(colors.accent, 0.24),
  },
  reviewPayloadLabel: {
    fontSize: 13,
    fontWeight: '600',
    opacity: 0.72,
  },
  reviewPayloadText: {
    marginTop: 10,
    fontSize: 17,
    lineHeight: 26,
  },
  reviewMetadataBlock: {
    marginTop: 18,
    padding: 14,
    borderRadius: 10,
    backgroundColor: colors.softSurface,
  },
  reviewMetadataTitle: {
    marginBottom: 8,
    fontSize: 13,
    fontWeight: '600',
    opacity: 0.72,
  },
  reviewMetadataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 14,
    paddingVertical: 5,
  },
  reviewMetadataLabel: {
    fontSize: 14,
    opacity: 0.62,
  },
  reviewMetadataValue: {
    flex: 1,
    textAlign: 'right',
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  findVerseButton: {
    marginTop: 26,
    paddingVertical: 16,
    alignItems: 'center',
    borderRadius: 12,
    backgroundColor: colors.primary,
  },
  findVerseText: {
    color: colors.inverseText,
    fontWeight: '700',
  },
  reviewSecondaryButton: {
    marginTop: 12,
    paddingVertical: 12,
    alignItems: 'center',
  },
  reviewSecondaryText: {
    color: colors.primary,
    fontWeight: '600',
  },
  sectionHeading: { marginTop: 24 },
  transcript: { marginTop: 8, marginBottom: 24, lineHeight: 22 },
  jsonBlock: {
    marginTop: 8, padding: 12, borderRadius: 8, backgroundColor: withAlpha(colors.primary, 0.06),
  },
  jsonText: { fontFamily: 'ui-monospace', fontSize: 13, lineHeight: 18 },
  anonymousLabel: { marginTop: 24 },
  anonymousText: { marginTop: 8, lineHeight: 22 },
  errorText: { color: colors.destructive, marginTop: 8, marginBottom: 16 },
  resetButton: {
    marginTop: 32, paddingVertical: 16, alignItems: 'center', borderRadius: 12,
    backgroundColor: colors.primary,
  },
  resetText: { color: colors.inverseText, fontWeight: '600' },

  primaryHeading: { marginTop: 8 },
  primaryRefBlock: {
    marginTop: 12,
    padding: 16,
    borderRadius: 12,
    backgroundColor: withAlpha(colors.accent, 0.12),
  },
  alternateRefBlock: {
    marginTop: 12,
    padding: 14,
    borderRadius: 10,
    backgroundColor: colors.softSurface,
  },
  refLabel: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  altRefLabel: { fontSize: 15, fontWeight: '600', marginBottom: 6 },
  verseText: { fontFamily: Fonts?.serif, fontSize: 18, lineHeight: 28 },
  altVerseText: { fontFamily: Fonts?.serif, fontSize: 16, lineHeight: 24 },
  translationLabel: { marginTop: 6, fontSize: 12, opacity: 0.7 },
  textErrorLabel: { marginTop: 4, opacity: 0.6, fontStyle: 'italic' },
  shortReason: { marginTop: 12, fontSize: 14, lineHeight: 20, opacity: 0.85 },
  altToggle: {
    marginTop: 16,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: withAlpha(colors.primary, 0.06),
  },
  altToggleText: { fontSize: 13 },
  alternatesBlock: { marginTop: 4 },
  providerBadge: { marginTop: 16, fontSize: 11, opacity: 0.5 },
  crisisBanner: {
    marginTop: 12,
    padding: 14,
    borderRadius: 10,
    backgroundColor: withAlpha(colors.destructive, 0.12),
    borderWidth: 1,
    borderColor: withAlpha(colors.destructive, 0.4),
  },
  crisisBannerText: { lineHeight: 20 },
  stoicStubBlock: {
    marginTop: 12,
    padding: 16,
    borderRadius: 12,
    backgroundColor: colors.softSurface,
  },
  stoicStubText: { marginTop: 8, lineHeight: 22 },
  unavailableBlock: {
    marginTop: 12,
    padding: 16,
    borderRadius: 12,
    backgroundColor: colors.softSurface,
  },
  unavailableTitle: { marginTop: 4 },
  unavailableText: { marginTop: 8, lineHeight: 22, opacity: 0.85 },
  lookupErrorBlock: { marginTop: 12 },
  retryButton: {
    alignSelf: 'flex-start',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    backgroundColor: colors.primary,
  },
  retryText: { color: colors.inverseText, fontWeight: '600' },
  });
}
