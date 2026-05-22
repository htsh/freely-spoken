# TestFlight Launch Checklist

**Goal:** Get `mic-check` onto TestFlight for internal beta testing using the free provider chain.

**Assumptions:**
- Backend is deployed and serving at `verses.hitesh.nyc`
- Bible API is accessible at `bible.hitesh.nyc` or via `bible-api.com`
- You have an Apple Developer account ($99/year, required for TestFlight)

---

## 1. Backend verification (do this first)

Before building the app, verify the deployed backend is healthy and the free provider chain is working:

```bash
curl -X POST https://verses.hitesh.nyc/lookup \
  -H "Content-Type: application/json" \
  -H "X-Lookup-Client-Secret: $LOOKUP_CLIENT_SECRET" \
  -d '{
    "appVariant": "christian",
    "anonymizedText": "A person is feeling anxious about an upcoming medical procedure.",
    "sentiment": "negative",
    "emotions": ["anxiety", "fear"],
    "confidence": 85
  }'
```

Expected: HTTP 200 with `primary.ref`, `alternates[]`, `provider`, `fallbackUsed`.

Also verify the Bible text fetch:
```bash
curl "https://bible-api.com/John%203:16?translation=web"
```

If the backend is unhealthy, fix it before burning build minutes.

---

## 2. Environment variables for the build

For local builds, create `.env` in the repo root with production values:

```bash
EXPO_PUBLIC_LOOKUP_API_URL=https://verses.hitesh.nyc
EXPO_PUBLIC_LOOKUP_CLIENT_SECRET=<your-lookup-client-secret>
EXPO_PUBLIC_APP_VARIANT=christian
```

For EAS cloud/TestFlight builds, create matching EAS environment variables in the `production` environment:

```bash
eas env:create --name EXPO_PUBLIC_LOOKUP_API_URL --value https://verses.hitesh.nyc --environment production --visibility plaintext
eas env:create --name EXPO_PUBLIC_LOOKUP_CLIENT_SECRET --value <your-lookup-client-secret> --environment production --visibility sensitive
eas env:create --name EXPO_PUBLIC_APP_VARIANT --value christian --environment production --visibility plaintext
```

**Important:** These are baked into the native build at build time via `app.config.js` `extra`. Changing them requires a rebuild. Client-side values are readable from the app binary, so do not treat `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` as a true server secret.

---

## 3. EAS configuration

### Helper package

Expo's current one-command helper is:

```bash
npx testflight
```

It walks through EAS project setup, bundle ID confirmation, Apple Developer login, signing credentials, production build, App Store Connect API key setup, and TestFlight submission.

### Install EAS CLI directly

```bash
npm install -g eas-cli
```

### Login

```bash
eas login
```

### Verify `eas.json`

The repo includes `eas.json` with:
- `production` build profile: iOS store/TestFlight build, release configuration, `production` EAS environment.
- `preview` build profile: internal distribution, release configuration, `preview` EAS environment.
- Empty `submit.production.ios` profile: usable interactively by `npx testflight` or `eas submit`; add `ascAppId` after creating the App Store Connect app if you want more non-interactive runs.

**Notes:**
- `preview` = EAS internal distribution (share via link, no TestFlight)
- `production` = TestFlight / App Store
- Fill in `ascAppId` after registering the app in App Store Connect if you want to skip the app-selection prompt.
- Increment `ios.buildNumber` in `app.json` before submitting a replacement build with the same `version`.

### Verify project is linked

```bash
eas project:info
```

Should show `mic-check` with project ID `9af03ee3-2eae-4f5c-b0fe-60200c3bd29d`.

---

## 4. Native build setup

### Prebuild (generates `ios/`)

```bash
npx expo prebuild
```

### Verify iOS bundle identifier

In `ios/miccheck.xcodeproj` or `app.json`, confirm:
- Bundle ID: `com.htsh.miccheck`
- No conflicts with existing App Store apps

---

## 5. iOS signing and provisioning

This is the most fiddly part. You need:

1. **Apple Developer Program** membership ($99/year, individual or organization)
2. **App Store Connect** app record for `com.htsh.miccheck`
3. **Signing certificate** (EAS handles this automatically if you use `eas build`)

### Option A: Let EAS handle signing (recommended)

```bash
eas build --platform ios --profile production
```

EAS will:
- Prompt for Apple ID credentials
- Generate certificates and provisioning profiles
- Register the bundle ID if needed

### Option B: Manual signing

Open `ios/miccheck.xcworkspace` in Xcode:
- Select your development team
- Resolve signing errors
- Build locally with `npx expo run:ios --device`
- Then upload via Xcode → Organizer → Distribute App

---

## 6. Build for TestFlight

Recommended first run:

```bash
npx testflight
```

This is the helper package for the whole build/sign/submit flow.

Manual EAS equivalent:

```bash
eas build --platform ios --profile production
```

This queues a cloud build. You can watch progress:
```bash
eas build:list
```

Build artifacts:
- `.ipa` file (iOS app package)
- Automatically submitted to App Store Connect if `submit` is configured

**First build** will take **15–30 minutes** (installs CocoaPods, builds native modules, uploads).

---

## 7. App Store Connect setup

After the build uploads:

1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Find `mic-check` (or create it if new)
3. Under **TestFlight → Internal Testing**:
   - Add yourself and trusted testers
   - Select the build that just uploaded
   - Submit for beta review

### Beta review requirements

Apple requires for TestFlight:
- **App name and subtitle**
- **Privacy policy URL** (required even for internal testing now)
- **Category** (e.g., Lifestyle, Reference)
- **Screenshots** (optional for internal, required for external)
- **Beta app description** (what testers should focus on)
- **Contact email**

### Privacy policy

Since this app records audio and sends anonymized text to a server, you need a privacy policy. Minimum contents:
- Audio is recorded on-device, transcribed on-device, never leaves device as audio
- Only anonymized text + sentiment metadata is sent to server
- No persistent storage of transcripts
- No user accounts or identifiers collected
- How to contact you for data deletion (even though nothing is stored)

Host this at a URL and link it in App Store Connect.
Before external beta or public review, also add an easily accessible in-app privacy-policy link.

---

## 8. Internal testing

Once beta review approves (usually **instant for internal**, 1–2 days for external):

1. Add testers by email in App Store Connect
2. Testers receive an email with TestFlight invite
3. They install the TestFlight app and accept the invite
4. `mic-check` appears in their TestFlight app list

---

## 9. Device requirements for testers

**Critical:** TestFlight users must have:
- **iPhone 15 Pro / 16 series** OR **M1+ iPad / Mac** (Apple Intelligence capable)
- **iOS 26 beta** installed
- **Apple Intelligence enabled** in Settings → Apple Intelligence & Siri

This eliminates ~90% of potential testers. Be explicit about this in your beta invitation.

---

## 10. What to test in TestFlight

### Smoke test matrix

| Flow | Expected |
|---|---|
| Record audio → stop | Private processing cue appears |
| Anonymization completes | Review screen shows the anonymized summary that will leave the device |
| Tap "Find My Verse" | Primary verse + 2 alternates appear |
| Tap primary verse | Full verse text renders |
| Tap "Record Again" | Clears everything, back to idle |
| No network connection | Graceful error, not a crash |
| Apple Intelligence unavailable | Clear error message, not infinite spinner |

Release/TestFlight builds should not show the dev-only debug link, raw transcript, sentiment JSON, guarded-anonymous debug block, provider name, model name, fallback status, or retry count.

### Log verification

Have testers report user-visible symptoms only:
- Whether lookup succeeds after tapping `Find My Verse`
- Any long delays over 10 seconds
- Any user-facing lookup error text

Provider diagnostics should come from backend logs or dev builds, not TestFlight UI:
- Which provider served the verse
- Whether fallback was used
- Retry count and `AllProvidersFailedError` events

---

## 11. Common failures

| Failure | Fix |
|---|---|
| Build fails with signing error | Run `eas build --platform ios`, let EAS manage certificates |
| `MissingLookupApiUrlError` | `EXPO_PUBLIC_LOOKUP_API_URL` not set at build time. Rebuild with `.env` file present. |
| Backend 401 | `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` mismatched with server `LOOKUP_CLIENT_SECRET` |
| Backend 500 / timeout | Free provider chain exhausted. Check server logs for `AllProvidersFailedError`. |
| Private processing stalls or no review summary appears | iOS 26 beta or Apple Intelligence not enabled on device |
| App crashes on recording | Microphone permission not granted. Check Settings → mic-check → Microphone. |
| TestFlight invite not received | Tester email must match Apple ID exactly. Resend from App Store Connect. |

---

## 12. From TestFlight to App Store (future)

When ready for public release:

1. Update version in `app.json` (`version` field)
2. Build with `eas build --platform ios --profile production`
3. In App Store Connect, select build, fill App Store metadata
4. Submit for App Review (1–3 days typical)
5. After approval, release or set phased rollout

---

## Quick reference commands

```bash
# Verify backend health
curl -X POST https://verses.hitesh.nyc/lookup -H "Content-Type: application/json" -H "X-Client-Secret: $SECRET" -d '{...}'

# Local dev build
npx expo run:ios --device

# Cloud build for TestFlight
eas build --platform ios --profile production

# Check build status
eas build:list

# Lint before building
npm run lint
```
