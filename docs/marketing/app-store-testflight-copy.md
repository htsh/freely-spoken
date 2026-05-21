# Freely Spoken App Store and TestFlight Copy

## Purpose

This copy package positions Freely Spoken as a privacy-first reflection app for App Store metadata, TestFlight beta information, and App Review notes.

The main privacy claim:

> Your audio and raw transcript stay on device. Only an anonymized summary and general emotional metadata are sent for passage lookup.

## Apple Wording Guidance

Use Apple-related language carefully. Do not imply Apple endorsement, and do not make "Apple Intelligence" the primary marketing hook.

Recommended public wording:

> Your voice is transcribed and anonymized on device using Apple's on-device speech and Foundation Models frameworks.

Reviewer-facing wording can be more technical:

> The app uses Apple's on-device speech recognition and Foundation Models framework to create an anonymized summary before any lookup request is sent.

Avoid:

- "Powered by Apple Intelligence" as a headline.
- Any wording that implies Apple sponsors, endorses, or operates the app.
- Overclaiming that no data ever leaves the device. The accurate claim is that raw audio and raw transcript do not leave the device; anonymized text and sentiment metadata do.

Useful references:

- [Foundation Models framework](https://developer.apple.com/documentation/FoundationModels)
- [Apple Intelligence for developers](https://developer.apple.com/apple-intelligence/)
- [Apple trademark guidelines](https://www.apple.com/legal/intellectual-property/guidelinesfor3rdparties.html)
- [Creating your App Store product page](https://developer.apple.com/app-store/product-page/)
- [TestFlight overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)

## Positioning

Freely Spoken is a private way to say what is on your mind and receive a short, relevant passage without sending your raw voice or transcript to the cloud.

## App Store Subtitle Options

App Store subtitle limit: 30 characters.

Recommended:

> Private voice reflection

Alternates:

- Speak privately. Reflect.
- Private scripture reflection
- A private verse for today

Rationale: "Private voice reflection" is broad, clear, and privacy-led without overexplaining the religious content in the subtitle.

## Promotional Text

App Store promotional text limit: 170 characters.

Recommended:

> Speak freely. Your voice and transcript stay on device; only an anonymized summary is sent to find a relevant passage.

## App Store Description

> Freely Spoken helps you speak honestly, privately, and receive a short passage for reflection.
>
> Record what is on your mind. The app transcribes your voice on device, anonymizes your words on device, and removes identifying details before anything is sent for lookup.
>
> Your audio is never uploaded. Your raw transcript is never uploaded. The app sends only an anonymized summary and general emotional metadata to find a relevant passage.
>
> Built for private, one-time reflection. No accounts. No chat history. No saved recordings.

## TestFlight Beta Description

> Freely Spoken is a privacy-first reflection app. Record what is on your mind, then receive a relevant passage.
>
> Please test the full flow: record, stop, review the transcript/anonymized version, receive a passage, and record again.
>
> Privacy is the main thing to verify: audio should never leave the device, raw transcript text should not be sent to the server, and the app should show only anonymized text before lookup.
>
> Requires an Apple Intelligence-capable device with Apple Intelligence enabled.

## TestFlight Features to Test

- Record audio and stop recording cleanly.
- Confirm on-device transcription appears.
- Confirm anonymized text appears before lookup.
- Confirm raw transcript text is not sent to the backend.
- Confirm the app receives a relevant passage.
- Confirm "Record Again" clears the session.
- Confirm unavailable Apple Intelligence or network failures show clear errors.

## App Review / Beta Review Notes

> Freely Spoken records audio, transcribes it on device, and uses Apple's on-device Foundation Models framework to create an anonymized summary and sentiment metadata. The backend receives only `{ appVariant, anonymizedText, sentiment, emotions, confidence }`. It does not receive audio, raw transcript text, recording duration, location, account data, or device identifiers.

## Screenshot Caption Direction

Use captions that make the privacy pipeline obvious:

- Speak privately
- Transcribed on device
- Anonymized before lookup
- Only the private summary is sent
- Receive a short passage

## Keyword Direction

Use only relevant terms. Avoid stuffing trademarked or unrelated keywords.

Potential keyword concepts:

- prayer
- reflection
- scripture
- bible
- verse
- private journal
- voice note
- anxiety
- encouragement
- devotion

Final keyword field should be tuned in App Store Connect against the 100-character limit.
