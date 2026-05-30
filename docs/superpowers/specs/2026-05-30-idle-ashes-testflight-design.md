# Idle Ashes TestFlight Design

## Context

Idle Ashes is the Dhammapada build variant of the existing Freely Spoken codebase. The backend already supports `appVariant: "dhammapada"` through the Dhammapada catalog adapter, and `https://verses.hitesh.nyc` already routes through Caddy to the running `mic-check-lookup` Docker service on the VPS.

The goal is to prepare a first internal TestFlight build of Idle Ashes as a separate Apple app and separate Expo/EAS project, while keeping one shared repository and one shared backend deployment.

## Decisions

- Use one shared backend deployment at `https://verses.hitesh.nyc`.
- Keep the existing lookup client secret for the first internal TestFlight pass; rotate it before broader or external testing.
- Ship Idle Ashes as a separate App Store Connect app with bundle identifier `com.htsh.idleashes`.
- Create or link a separate Expo/EAS project under owner `arlodog` with slug `idle-ashes`.
- Keep the codebase shared. `EXPO_PUBLIC_APP_VARIANT=dhammapada` selects Idle Ashes identity, brand tokens, assets, and lookup behavior.
- Target internal TestFlight testers first.

## Brand Direction

Idle Ashes should feel quiet, private, reflective, literate, and grounded. The primary logo should be simple enough to work as a flat app icon: abstract ash fragments and a restrained ember, paired with a lowercase `idle ashes` wordmark.

The more detailed smoke-and-embers image direction should be used as brand atmosphere, not as the primary logo. It belongs in splash/onboarding imagery, App Store screenshots, or future marketing surfaces where fine ash particles and smoke can survive the rendering size.

Core palette:

- Warm ivory background
- Deep charcoal text and icon forms
- Ash gray secondary surfaces
- Muted clay accents
- Restrained copper ember highlight

Avoid lotus, dharma wheel, temple, monk, mandala, incense burner, bowl/cup, candle, cartoon flame, and generic wellness imagery.

## App Identity

`app.config.js` should remain the owner of variant-specific native identity. The Dhammapada variant should define:

- Display name: `Idle Ashes`
- iOS bundle identifier: `com.htsh.idleashes`
- Android package: `com.htsh.idleashes`
- URL scheme: `idleashes`
- Slug for the Idle Ashes EAS project: `idle-ashes`
- Dedicated icon and splash assets
- Dedicated `extra.eas.projectId` once the separate EAS project exists

Freely Spoken must keep its current bundle identifier, EAS project id, and assets unchanged.

## App Styling

The app should become variant-aware at the brand-token level. Freely Spoken keeps the current navy/gold/ivory treatment. Idle Ashes gets its own token set:

- Background: warm ivory
- Primary text: deep charcoal
- Muted text: warm ash gray
- Primary action: charcoal
- Accent: copper ember
- Soft panel: ash/parchment surface
- Destructive/error: keep a distinct accessible red

The home screen should use a lowercase Idle Ashes wordmark feel, a restrained record control, and less radiant/gold treatment than Freely Spoken. Result cards should read as quiet passage cards: high legibility, serif-forward passage text, muted metadata, and restrained alternate controls.

No new product features are in scope for this pass. The app remains single-turn: record, transcribe, anonymize, review outbound summary, lookup passage, show result.

## Assets

Generate and commit dedicated Idle Ashes assets:

- Primary brand mark, preferably SVG plus PNG
- Wordmark or lockup for reference
- iOS app icon source and generated icon
- Splash icon/image
- Android adaptive icon foreground/background/monochrome if Android assets are kept in sync
- Brand README update documenting the Idle Ashes asset direction

The final implementation should prefer deterministic/generated vector or scripted asset generation where practical, matching the existing Freely Spoken asset generator pattern. AI-generated raster imagery can be used as reference or atmospheric source material, but app icons and reusable marks should end as clean local assets.

## Backend

The shared backend is already deployed on `vps2`:

- Caddy route: `verses.hitesh.nyc -> 127.0.0.1:7777`
- Docker container: `mic-check-lookup:latest`
- Container mapping: `127.0.0.1:7777 -> 8080`
- Health check: `GET https://verses.hitesh.nyc/healthz`

No second backend should be created for the first TestFlight pass. The Idle Ashes build should use:

```text
EXPO_PUBLIC_LOOKUP_API_URL=https://verses.hitesh.nyc
EXPO_PUBLIC_LOOKUP_CLIENT_SECRET=<current shared lookup client secret>
EXPO_PUBLIC_APP_VARIANT=dhammapada
```

The shared lookup client secret should remain in local/EAS environment configuration and should not be committed to tracked documentation or source.

Before external testing, rotate `LOOKUP_CLIENT_SECRET` on the server and in the app build environment. Treat the client secret as a request gate only, not a true secret, because mobile binary values are recoverable.

## Release Flow

The first release target is an iOS production build submitted to App Store Connect for internal TestFlight.

Required release steps:

1. Create or link the Idle Ashes EAS project under `arlodog`.
2. Make `app.config.js` resolve the Idle Ashes EAS project id only for the Dhammapada variant.
3. Ensure EAS build profile `production-idleashes` injects the Dhammapada variant and lookup configuration.
4. Create or verify the Apple bundle id `com.htsh.idleashes`.
5. Create the App Store Connect app for Idle Ashes.
6. Run validation locally: typecheck, tests, and config inspection for the Idle Ashes profile.
7. Build iOS with `production-idleashes`.
8. Submit the build to App Store Connect.
9. Add internal testers in TestFlight and verify the real-device flow.

## Testing

Local verification should cover:

- `npm test`
- `npm run typecheck`
- `npm run lint` if it is currently passing or failures are understood
- Expo config output for `EXPO_PUBLIC_APP_VARIANT=dhammapada`
- Backend health check against `https://verses.hitesh.nyc/healthz`
- Optional curl lookup smoke test for `appVariant: "dhammapada"` using the configured client secret

Device/TestFlight verification should cover:

- App installs as Idle Ashes beside Freely Spoken.
- App icon and splash show Idle Ashes assets.
- Permission prompts say Idle Ashes.
- Recording starts and stops.
- Transcription runs on device.
- Private summary review shows only anonymized outbound data.
- Lookup returns a Dhammapada passage from the backend.
- Crisis handling still shows the support banner and avoids unsafe passage selection.
- Debug route is not reachable in release builds.

## Out Of Scope

- Public App Store submission
- External TestFlight group setup
- Backend domain change
- Separate Idle Ashes backend deployment
- Account system, history, chat, or multi-turn behavior
- New catalog content or Dhammapada selection logic changes
- Client-secret rotation, except as a documented pre-external-testing task
