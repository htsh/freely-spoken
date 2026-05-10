import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View, useColorScheme } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useSentimentAnalyzer } from '@/hooks/use-sentiment-analyzer';

const FIXTURES = [
  "My name is Maya Patel, I work at Northstar Clinic in Denver, and after my surgery on March 3 I feel scared and angry.",
  "I keep waking up at 3am because my brother Aaron owes me $4,800 and our court date in Queens is next Friday.",
  "Sarah from Cedar Ridge Elementary told everyone about my daughter's diagnosis, and I feel betrayed.",
  "I love my manager Jordan at Finley Bank, but the performance review on April 12 left me humiliated and confused.",
];

export default function DebugScreen() {
  const colorScheme = useColorScheme() ?? 'light';
  const [text, setText] = useState('');
  const { result, raw, isAnalyzing, error, analyze, reset } = useSentimentAnalyzer();

  const inputColors = colorScheme === 'dark'
    ? { color: '#ECEDEE', borderColor: '#333', backgroundColor: '#1c1f21' }
    : { color: '#11181C', borderColor: '#ddd', backgroundColor: '#fafafa' };

  const onAnalyze = () => {
    const trimmed = text.trim();
    if (!trimmed || isAnalyzing) return;
    analyze(trimmed);
  };

  const onClear = () => {
    setText('');
    reset();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ThemedView style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.header}>
            <Pressable onPress={() => router.back()} hitSlop={12}>
              <ThemedText style={styles.back}>← Back</ThemedText>
            </Pressable>
            <ThemedText type="title" style={styles.title}>Sentiment + Privacy Debug</ThemedText>
          </View>

          <ThemedText style={styles.hint}>
            Type a transcript and run it through the same on-device analyzer the app uses.
            Skips recording and STT so you can inspect sentiment, anonymization, and raw model output.
          </ThemedText>

          <TextInput
            style={[styles.input, inputColors]}
            placeholder="Paste or type a transcript here..."
            placeholderTextColor={colorScheme === 'dark' ? '#666' : '#999'}
            value={text}
            onChangeText={setText}
            multiline
            textAlignVertical="top"
            autoCapitalize="sentences"
            autoCorrect
          />

          <View style={styles.buttonRow}>
            <Pressable
              style={[styles.button, styles.primaryButton, (isAnalyzing || !text.trim()) && styles.disabled]}
              onPress={onAnalyze}
              disabled={isAnalyzing || !text.trim()}
            >
              <ThemedText style={styles.primaryButtonText}>
                {isAnalyzing ? 'Analyzing…' : 'Analyze'}
              </ThemedText>
            </Pressable>
            <Pressable style={[styles.button, styles.secondaryButton]} onPress={onClear}>
              <ThemedText style={styles.secondaryButtonText}>Clear</ThemedText>
            </Pressable>
          </View>

          <ThemedText type="subtitle" style={styles.sectionLabel}>Fixtures</ThemedText>
          <View style={styles.fixtureColumn}>
            {FIXTURES.map((fixture) => (
              <Pressable
                key={fixture}
                style={styles.fixtureRow}
                onPress={() => setText(fixture)}
              >
                <ThemedText style={styles.fixtureText} numberOfLines={3}>
                  {fixture}
                </ThemedText>
              </Pressable>
            ))}
          </View>

          {error && (
            <View style={styles.errorBox}>
              <ThemedText style={styles.errorText}>{error}</ThemedText>
            </View>
          )}

          {result && (
            <>
              <ThemedText type="subtitle" style={styles.sectionLabel}>Normalized</ThemedText>
              <View style={styles.resultBlock}>
                <ThemedText style={styles.resultLine}>
                  <ThemedText style={styles.resultLabel}>sentiment: </ThemedText>
                  {result.sentiment}
                </ThemedText>
                <ThemedText style={styles.resultLine}>
                  <ThemedText style={styles.resultLabel}>confidence: </ThemedText>
                  {Math.round(result.confidence * 100)}%
                </ThemedText>
                <ThemedText style={styles.resultLine}>
                  <ThemedText style={styles.resultLabel}>emotions: </ThemedText>
                  {result.emotions.length > 0 ? result.emotions.join(', ') : '(none)'}
                </ThemedText>
                <ThemedText style={styles.resultLine}>
                  <ThemedText style={styles.resultLabel}>anonymizedText: </ThemedText>
                  {result.anonymizedText}
                </ThemedText>
              </View>
            </>
          )}

          {raw && (
            <>
              <View style={styles.rawHeader}>
                <ThemedText type="subtitle" style={styles.sectionLabel}>Raw model output</ThemedText>
                <View style={[styles.badge, raw.strategy === 'object' ? styles.badgeOk : styles.badgeWarn]}>
                  <ThemedText style={styles.badgeText}>{raw.strategy}</ThemedText>
                </View>
              </View>
              <View style={styles.codeBlock}>
                <ThemedText style={styles.codeText}>{raw.value}</ThemedText>
              </View>
            </>
          )}
        </ScrollView>
      </ThemedView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  container: { flex: 1 },
  content: { paddingHorizontal: 20, paddingBottom: 60 },
  header: { marginTop: 8, marginBottom: 16 },
  back: { opacity: 0.7, marginBottom: 8 },
  title: { fontSize: 26 },
  hint: { opacity: 0.7, marginBottom: 16, lineHeight: 20 },
  input: {
    minHeight: 120,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    lineHeight: 22,
  },
  buttonRow: { flexDirection: 'row', gap: 10, marginTop: 12 },
  button: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
  },
  primaryButton: { backgroundColor: '#0a7ea4' },
  primaryButtonText: { color: '#fff', fontWeight: '600' },
  secondaryButton: { backgroundColor: 'rgba(128,128,128,0.2)' },
  secondaryButtonText: { fontWeight: '600' },
  disabled: { opacity: 0.5 },
  sectionLabel: { marginTop: 24, marginBottom: 8 },
  fixtureColumn: { gap: 6 },
  fixtureRow: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: 'rgba(128,128,128,0.12)',
  },
  fixtureText: { fontSize: 14, opacity: 0.85 },
  resultBlock: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(10,126,164,0.08)',
    gap: 4,
  },
  resultLine: { fontSize: 15 },
  resultLabel: { fontWeight: '600', opacity: 0.7 },
  rawHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, marginTop: 24 },
  badgeOk: { backgroundColor: 'rgba(52,199,89,0.2)' },
  badgeWarn: { backgroundColor: 'rgba(255,149,0,0.25)' },
  badgeText: { fontSize: 12, fontWeight: '600' },
  codeBlock: {
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(0,0,0,0.06)',
  },
  codeText: { fontFamily: 'ui-monospace', fontSize: 13, lineHeight: 18 },
  errorBox: {
    marginTop: 16,
    padding: 12,
    borderRadius: 10,
    backgroundColor: 'rgba(255,59,48,0.12)',
  },
  errorText: { color: '#ff3b30' },
});
