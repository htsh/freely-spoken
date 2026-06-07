// Pure helper for the response-lookup loading cue. No React or React Native
// dependencies — testable in any JS runtime.

// Caption lines shown (and cycled) while the backend selects a passage.
// `noun` is the variant's response noun, e.g. 'verse' or 'passage'.
export function buildLookupCaptions(noun: string): string[] {
  return [
    `Finding your ${noun}`,
    'Reading your reflection',
    `Choosing a fitting ${noun}`,
    'Almost there…',
  ];
}
