// Dynamic Expo config — selects a product flavor at build time and injects the
// EXPO_PUBLIC_* values into `extra` (resolving the "$EXPO_PUBLIC_*" placeholders
// in app.json so Constants.expoConfig.extra holds concrete values at runtime).
//
// The static base config lives in app.json and is the Freely Spoken / Christian
// default. This file overrides per-variant native identity (display name, iOS
// bundle id, Android package, URL scheme, icon) and rewrites the product name
// inside every user-facing permission string, driven by EXPO_PUBLIC_APP_VARIANT.
//
//   EXPO_PUBLIC_APP_VARIANT=dhammapada npx expo run:ios --device   # Idle Ashes
//   (unset / christian)                                            # Freely Spoken
//
// One codebase, multiple product variants. The runtime JS also reads the variant
// via services/lookup-request.ts getBuildAppVariant().

const lookupApiUrl = process.env.EXPO_PUBLIC_LOOKUP_API_URL;
const lookupClientSecret = process.env.EXPO_PUBLIC_LOOKUP_CLIENT_SECRET;
const appVariant = process.env.EXPO_PUBLIC_APP_VARIANT || process.env.APP_VARIANT || 'christian';

// The product name as written in app.json — every occurrence in user-facing
// strings (permission prompts) is swapped for the active variant's name.
const BASE_NAME = 'Freely Spoken';

// Each variant builds against its own App Store Connect app and EAS project.
// Project ids are not secrets.
const FREELY_SPOKEN_EAS_PROJECT_ID = '9af03ee3-2eae-4f5c-b0fe-60200c3bd29d';
const IDLE_ASHES_EAS_PROJECT_ID = '7994ef0a-b5ad-4924-b93f-f99f6bef8818'; // @arlodog/idle-ashes

// Freely Spoken (default) native identity / assets, reused by both christian and
// stoic so the shipped app is unaffected.
const FREELY_SPOKEN_ASSETS = {
  slug: 'mic-check',
  icon: './assets/images/icon.png',
  splashImage: './assets/images/splash-icon.png',
  splashBackgroundColor: '#F7F1E8',
  androidAdaptiveIcon: {
    foregroundImage: './assets/images/android-icon-foreground.png',
    backgroundImage: './assets/images/android-icon-background.png',
    monochromeImage: './assets/images/android-icon-monochrome.png',
    backgroundColor: '#F7F1E8',
  },
  favicon: './assets/images/favicon.png',
  easProjectId: FREELY_SPOKEN_EAS_PROJECT_ID,
};

// Per-variant native identity. christian MUST keep the existing bundle id /
// scheme so the shipped Freely Spoken app is unaffected.
const VARIANTS = {
  christian: {
    name: 'Freely Spoken',
    iosBundleId: 'com.htsh.miccheck',
    androidPackage: 'com.htsh.miccheck',
    scheme: 'miccheck',
    ...FREELY_SPOKEN_ASSETS,
  },
  dhammapada: {
    name: 'Idle Ashes',
    slug: 'idle-ashes',
    iosBundleId: 'com.htsh.idleashes',
    androidPackage: 'com.htsh.idleashes',
    scheme: 'idleashes',
    icon: './assets/images/idle-ashes-icon.png',
    splashImage: './assets/images/idle-ashes-splash-icon.png',
    splashBackgroundColor: '#F4EEE6',
    androidAdaptiveIcon: {
      foregroundImage: './assets/images/idle-ashes-android-icon-foreground.png',
      backgroundImage: './assets/images/idle-ashes-android-icon-background.png',
      monochromeImage: './assets/images/idle-ashes-android-icon-monochrome.png',
      backgroundColor: '#F4EEE6',
    },
    favicon: './assets/images/idle-ashes-favicon.png',
    easProjectId: IDLE_ASHES_EAS_PROJECT_ID,
  },
  stoic: {
    name: 'Freely Spoken (Stoic)',
    iosBundleId: 'com.htsh.miccheck.stoic',
    androidPackage: 'com.htsh.miccheck.stoic',
    scheme: 'miccheckstoic',
    ...FREELY_SPOKEN_ASSETS,
  },
};

function renameProduct(value, to) {
  return typeof value === 'string' ? value.split(BASE_NAME).join(to) : value;
}

module.exports = ({ config }) => {
  const variant = VARIANTS[appVariant] || VARIANTS.christian;

  // Native identity
  config.name = variant.name;
  config.slug = variant.slug;
  config.scheme = variant.scheme;
  config.icon = variant.icon;
  config.web = { ...(config.web || {}), favicon: variant.favicon };
  config.ios = { ...(config.ios || {}), bundleIdentifier: variant.iosBundleId };
  config.android = {
    ...(config.android || {}),
    package: variant.androidPackage,
    adaptiveIcon: {
      ...(config.android?.adaptiveIcon || {}),
      ...(variant.androidAdaptiveIcon || {}),
    },
  };

  // iOS Info.plist permission descriptions ("Allow Freely Spoken to ...")
  if (config.ios.infoPlist) {
    const infoPlist = { ...config.ios.infoPlist };
    for (const k of Object.keys(infoPlist)) {
      infoPlist[k] = renameProduct(infoPlist[k], variant.name);
    }
    config.ios.infoPlist = infoPlist;
  }

  // Config-plugin permission strings (expo-av, expo-speech-recognition) and the
  // per-variant splash image / background.
  config.plugins = (config.plugins || []).map((plugin) => {
    if (!Array.isArray(plugin)) return plugin;
    const [name, options] = plugin;
    const next = options && typeof options === 'object' ? { ...options } : options;

    if (name === 'expo-splash-screen' && next && typeof next === 'object') {
      return [name, {
        ...next,
        image: variant.splashImage,
        backgroundColor: variant.splashBackgroundColor,
        dark: {
          ...(next.dark || {}),
          backgroundColor: variant.splashBackgroundColor,
        },
      }];
    }

    if (next && typeof next === 'object') {
      for (const k of Object.keys(next)) next[k] = renameProduct(next[k], variant.name);
      return [name, next];
    }
    return plugin;
  });

  // Inject EXPO_PUBLIC_* into extra and pin the resolved variant (replacing the
  // "$EXPO_PUBLIC_APP_VARIANT" placeholder from app.json). The EAS project id is
  // set per variant so each builds against its own Expo project.
  config.extra = {
    ...(config.extra || {}),
    eas: {
      ...(config.extra?.eas || {}),
      // Each variant owns its EAS project id explicitly. dhammapada is undefined
      // until its Expo project is created (do not inherit the Freely Spoken id).
      projectId: variant.easProjectId,
    },
    lookupApiUrl,
    lookupClientSecret,
    appVariant,
  };

  return config;
};
