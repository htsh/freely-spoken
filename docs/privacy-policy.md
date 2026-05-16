# Privacy Policy for mic-check

**Last updated:** May 16, 2026

## Overview

mic-check is a privacy-first iOS app that helps you reflect on what you're going through by offering a relevant passage. We designed the app to collect as little data as possible and to process everything sensitive on your device before anything leaves it.

## What data we collect

### Audio recordings

When you tap the record button, the app captures audio using your device's microphone. This audio is processed entirely on your device and is **never stored, never uploaded, and never leaves your device**.

### Speech transcription

Your recording is transcribed to text on your device using Apple's built-in speech recognition engine. The raw transcript exists only in temporary memory during your session and is **never stored or transmitted**.

### Anonymized text and sentiment

The app uses Apple Intelligence (on-device machine learning) to:
- Understand the general emotional tone of what you shared
- Produce an anonymized summary that removes names, places, dates, and identifying details

**Only this anonymized summary and emotional metadata** are sent to our server to find a relevant passage. For example:

> "A person is feeling anxious about a significant life change. Sentiment: concern."

We cannot identify you from this data, and we do not link it to your device, your Apple ID, or any profile.

## What our server receives

When you complete a recording, our backend receives exactly this:

- The anonymized summary of your situation
- General sentiment labels (e.g., "positive," "negative," "anxious")
- A confidence score
- Which version of the app you're using (e.g., Christian)

Our server **does not** receive:
- Your audio recording
- Your raw transcript
- Your name, email, or Apple ID
- Your device identifier
- Your location
- Any recording metadata (duration, file path, timestamp)

## How we use the data

The anonymized summary is used only to select a relevant passage and returned to your device immediately. We do not:
- Store your requests on our servers
- Use your data to train models
- Share your data with third parties
- Sell your data
- Build profiles or histories

## Third-party services

### Bible text lookup

To show you the full text of a selected passage, the app may fetch canonical verse text from a public Bible API (`bible-api.com`). This request contains only a book, chapter, and verse reference — no personal information.

### Apple services

On-device speech recognition and sentiment analysis are performed by Apple's operating system frameworks (`SFSpeechRecognizer` and Apple Foundation Models). These processes run locally on your device and are governed by [Apple's Privacy Policy](https://www.apple.com/legal/privacy/).

## Data retention

**We do not retain your data.** Because no personal information is transmitted to our servers, there is nothing for us to store or delete. Audio and raw transcripts exist only momentarily in your device's memory and are discarded as soon as the session ends. The app does not use persistent storage.

## Your rights

Because we do not store personal data, there is no account to delete or data to export. If you have questions about this policy or concerns about your privacy, you can contact us at the address below.

## Children

This app is not intended for children under 13. We do not knowingly collect any information from children.

## Changes to this policy

If we make material changes to this policy, we will update the date above and notify users through the app or App Store release notes.

## Contact

For privacy questions or concerns, contact:

**[Your name or support email]**
**[Your preferred contact method]**

---

*This privacy policy is intentionally short because the app is intentionally minimal with respect to data collection.*
