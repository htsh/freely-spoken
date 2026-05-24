# TestFlight Launch Checklist

**Goal:** Test `mic-check` on a real iPhone, ship repeat TestFlight builds, and prepare the same production build path for App Store review.

**Assumptions:**
- Backend is deployed and serving at `verses.hitesh.nyc`
- Bible API is accessible at `bible.hitesh.nyc` or via `bible-api.com`
- You have an Apple Developer account ($99/year, required for TestFlight)

This document covers three separate paths:

| Path | Use it for | Uploads to App Store Connect? |
|---|---|---|
| Local device build | Fast testing on your own phone from Xcode/Expo CLI | No |
| EAS production build + submit | TestFlight and App Store Connect processing | Yes |
| App Store review submission | Public release after TestFlight validation | Uses an already uploaded build |

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

## 3. Test locally on your phone without EAS Build

Use this for development and release-candidate smoke testing before spending EAS build time. It builds on your Mac with Xcode and installs directly to a connected device. It does **not** create a TestFlight build and it does **not** upload anything to App Store Connect.

This app cannot run in Expo Go because it uses native modules for audio, speech recognition, and Apple Foundation Models.

### One-time device setup

- Install Xcode and open it once so it can install command-line components.
- Connect the iPhone by USB or pair it in Xcode.
- Trust the Mac on the phone.
- Enable Developer Mode on the phone: Settings -> Privacy & Security -> Developer Mode.
- Make sure the phone is Apple Intelligence-capable, running iOS 26+, and has Apple Intelligence enabled.
- If signing fails, open `ios/miccheck.xcworkspace`, select the app target, and set your Apple Developer team under Signing & Capabilities.

### Normal local dev build

```bash
npm install
npx expo prebuild
npx expo run:ios --device
```

`npx expo run:ios --device` builds the generated Xcode project, prompts for a connected device, installs the app, launches it, and starts Metro. This is the fastest way to test recording, on-device transcription, anonymization, and lookup on your own phone.

### When native config changed

Run prebuild again after changing dependencies, Expo plugins, permissions, icons, splash config, `app.json` native settings, or anything else that affects the generated native project:

```bash
npx expo prebuild
npx expo run:ios --device
```

If the generated project looks stale or signing/build settings are confused, regenerate it cleanly:

```bash
npx expo prebuild --clean
npx expo run:ios --device --no-build-cache
```

`ios/` is generated and gitignored, so durable app changes belong in `app.json`, TypeScript, assets, config plugins, or package dependencies, not hand edits inside `ios/`.

### Release-like local smoke test

Before making a TestFlight build, also run a local Release configuration when practical:

```bash
npx expo run:ios --device --configuration Release
```

This is still a local install, not an EAS Build. Use it to catch obvious Release-only behavior, especially that `__DEV__` debug affordances are hidden.

### Local smoke checklist

| Check | Expected |
|---|---|
| Launch app | No `MissingLookupApiUrlError`; production `.env` values are baked in |
| Record -> stop | Private processing cue appears |
| Transcription/anonymization | Review screen shows only anonymized text |
| Tap "Find My Verse" | Backend returns primary verse + alternates |
| Airplane mode during lookup | Graceful user-facing error |
| Release local build | No `/debug` link, raw transcript, provider details, retry count, or fallback status in UI |

---

## 4. EAS configuration

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
- `cli.appVersionSource` is `local`, so App Store version values come from `app.json`.
- Fill in `ascAppId` after registering the app in App Store Connect if you want to skip the app-selection prompt.
- Increment `ios.buildNumber` in `app.json` before submitting a replacement build with the same `version`.

### Verify project is linked

```bash
eas project:info
```

Should show `mic-check` with project ID `9af03ee3-2eae-4f5c-b0fe-60200c3bd29d`.

---

## 5. Native build setup

### Prebuild (generates `ios/`)

```bash
npx expo prebuild
```

### Verify iOS bundle identifier

In `ios/miccheck.xcodeproj` or `app.json`, confirm:
- Bundle ID: `com.htsh.miccheck`
- No conflicts with existing App Store apps

---

## 6. iOS signing and provisioning

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

## 7. Build and submit another TestFlight build

### Version fields

This repo uses local app versioning:

| File field | Apple field | Change when |
|---|---|---|
| `expo.version` in `app.json` | `CFBundleShortVersionString` / App Store marketing version | The user-facing release version changes, for example `1.0.0` -> `1.0.1` |
| `expo.ios.buildNumber` in `app.json` | `CFBundleVersion` / App Store build number | Every TestFlight/App Store upload, even if `expo.version` stays the same |

App Store Connect rejects duplicate builds. If you see "You've already submitted this build of the app," increment `expo.ios.buildNumber`, make a fresh production build, then submit that new build. Do not resubmit an old `.ipa` with the same build number.

For this repo, keep `ios.buildNumber` monotonically increasing and commit the bump before building. `package.json` `version` is not what App Store Connect reads.

### Replacement TestFlight build for the same app version

Example: replacing `1.0.0` build `3` with another `1.0.0` candidate:

```json
{
  "expo": {
    "version": "1.0.0",
    "ios": {
      "buildNumber": "4"
    }
  }
}
```

Then build and submit:

```bash
npm run lint
eas build --platform ios --profile production --message "1.0.0 build 4"
eas build:list --platform ios --limit 5
eas submit --platform ios --profile production --latest --wait --verbose
```

Safer submit path when there are multiple recent builds:

```bash
eas submit --platform ios --profile production --id <eas-build-id> --wait --verbose
```

Only use `--latest` after confirming the latest iOS production build is the new build number you intend to upload.

### New app version

For a user-facing version bump, increment both fields:

```json
{
  "expo": {
    "version": "1.0.1",
    "ios": {
      "buildNumber": "5"
    }
  }
}
```

Then use the same build/submit commands. The `buildNumber` still moves forward; avoid resetting it.

### One-command helper

Expo's helper can run the whole build/sign/submit flow interactively:

```bash
npx testflight
```

The manual commands above are preferred when you want an explicit committed build-number bump. If you use `npx testflight`, inspect `app.json` afterward and commit any version change it makes.

### Manual EAS build without immediate submit

```bash
eas build --platform ios --profile production
```

This queues a cloud build. You can watch progress:
```bash
eas build:list --platform ios --limit 5
```

Build artifacts:
- `.ipa` file (iOS app package)
- Submitted to App Store Connect only when you run `eas submit` or build with `--auto-submit`

**First build** will take **15–30 minutes** (installs CocoaPods, builds native modules, uploads).

To build and submit in one command:

```bash
eas build --platform ios --profile production --auto-submit --message "1.0.0 build 4"
```

---

## 8. App Store Connect setup

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
- **App privacy answers** before public submission

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

## 9. Internal testing

Once beta review approves (usually **instant for internal**, 1–2 days for external):

1. Add testers by email in App Store Connect
2. Testers receive an email with TestFlight invite
3. They install the TestFlight app and accept the invite
4. `mic-check` appears in their TestFlight app list

---

## 10. Device requirements for testers

**Critical:** TestFlight users must have:
- **iPhone 15 Pro / 16 series** OR **M1+ iPad / Mac** (Apple Intelligence capable)
- **iOS 26 beta** installed
- **Apple Intelligence enabled** in Settings → Apple Intelligence & Siri

This eliminates ~90% of potential testers. Be explicit about this in your beta invitation.

---

## 11. What to test in TestFlight

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

## 12. Common failures

| Failure | Fix |
|---|---|
| Build fails with signing error | Run `eas build --platform ios`, let EAS manage certificates |
| `MissingLookupApiUrlError` | `EXPO_PUBLIC_LOOKUP_API_URL` not set at build time. Rebuild with `.env` file present. |
| Backend 401 | `EXPO_PUBLIC_LOOKUP_CLIENT_SECRET` mismatched with server `LOOKUP_CLIENT_SECRET` |
| Backend 500 / timeout | Free provider chain exhausted. Check server logs for `AllProvidersFailedError`. |
| Private processing stalls or no review summary appears | iOS 26 beta or Apple Intelligence not enabled on device |
| App crashes on recording | Microphone permission not granted. Check Settings → mic-check → Microphone. |
| TestFlight invite not received | Tester email must match Apple ID exactly. Resend from App Store Connect. |
| EAS submit says the build was already submitted | Increment `expo.ios.buildNumber`, create a fresh production build, then submit the new build ID. |

---

## 13. Prepare for App Store submission

App Store release uses the same uploaded production build path as TestFlight. The extra work is App Store Connect metadata, privacy/compliance answers, review notes, and final review submission.

### Code and release readiness

- Full TestFlight smoke pass on an Apple Intelligence-capable real device.
- `npm run lint` passes.
- Production backend is healthy and has enough provider capacity for review.
- `app.json` has the public `expo.version` and a new `expo.ios.buildNumber`.
- `ITSAppUsesNonExemptEncryption` remains `false` unless the app starts using non-exempt encryption.
- Release/TestFlight UI exposes no debug affordances: no `/debug` access, raw transcript, sentiment JSON, provider/model name, fallback status, or retry count.
- Error states are reviewable: Apple Intelligence unavailable, microphone denied, speech recognition denied, network failure, backend failure.
- Privacy policy is hosted at a stable URL and linked from App Store Connect. Add an in-app privacy-policy link before public review.
- The App Review build can be used without an account, login, seed data, or reviewer-only setup.

### App Store Connect metadata

Use `docs/marketing/app-store-testflight-copy.md` as the starting copy package. Prepare:

- App name, subtitle, promotional text, description, keywords, support URL, and privacy policy URL.
- Category, age rating, copyright, pricing, availability, and release mode.
- Required iPhone screenshots, and iPad screenshots if the app remains marked as tablet-supported.
- App Privacy answers that match the real payload: audio and raw transcript stay on device; the server receives only `{ appVariant, anonymizedText, sentiment, emotions, confidence }`.
- Review contact information.
- App Review notes explaining the device requirements and test flow.

Recommended review note:

```text
Freely Spoken requires an Apple Intelligence-capable iPhone or iPad running iOS 26+ with Apple Intelligence enabled. No account is required.

Test flow:
1. Grant microphone and speech recognition permissions.
2. Tap record, speak a short concern, then stop.
3. Wait for on-device transcription and anonymization.
4. Review the anonymized text and tap "Find My Verse."
5. Confirm that a primary verse and alternate references appear.

Privacy boundary: audio and raw transcript stay on device. The backend receives only appVariant, anonymizedText, sentiment, emotions, and confidence for passage lookup.
```

### Final submission steps

1. Decide whether this is a replacement build or a new public version.
2. Update `app.json`:
   - Replacement build: increment only `expo.ios.buildNumber`.
   - New public version: increment `expo.version` and `expo.ios.buildNumber`.
3. Build and submit:

   ```bash
   npm run lint
   eas build --platform ios --profile production --message "<version> build <number>"
   eas submit --platform ios --profile production --id <eas-build-id> --wait --verbose
   ```

4. Wait for Apple to finish processing the uploaded build.
5. In App Store Connect, open the app version under the App Store tab.
6. Select the processed build.
7. Complete metadata, screenshots, privacy, age rating, pricing, availability, and review notes.
8. Click **Add for Review**, then submit the draft submission for App Review.
9. After approval, release manually or use phased release.

---

## Quick reference commands

```bash
# Verify backend health
curl -X POST https://verses.hitesh.nyc/lookup -H "Content-Type: application/json" -H "X-Lookup-Client-Secret: $LOOKUP_CLIENT_SECRET" -d '{...}'

# Local dev build
npx expo run:ios --device

# Local release-like build
npx expo run:ios --device --configuration Release

# Cloud build for TestFlight
eas build --platform ios --profile production

# Check build status
eas build:list --platform ios --limit 5

# Submit a specific new build
eas submit --platform ios --profile production --id <eas-build-id> --wait --verbose

# Build and auto-submit
eas build --platform ios --profile production --auto-submit --message "<version> build <number>"

# Lint before building
npm run lint
```

## References

- [Expo: `npx testflight` command](https://docs.expo.dev/build-reference/npx-testflight/)
- [Expo: Submit to the Apple App Store](https://docs.expo.dev/submit/ios/)
- [Expo: Local app development](https://docs.expo.dev/guides/local-app-development/)
- [Expo: Local builds](https://docs.expo.dev/build-reference/local-builds/)
- [Expo: iOS Developer Mode](https://docs.expo.dev/guides/ios-developer-mode/)
- [Apple: Submit an app](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app)
- [Apple: App information](https://developer.apple.com/help/app-store-connect/reference/app-information/)
- [Apple: Upload app previews and screenshots](https://developer.apple.com/help/app-store-connect/manage-app-information/upload-app-previews-and-screenshots)
