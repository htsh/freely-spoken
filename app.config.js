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

// Per-variant native identity. christian MUST keep the existing bundle id /
// scheme so the shipped Freely Spoken app is unaffected. The Idle Ashes bundle
// ids below are placeholders under the existing com.htsh namespace — set them to
// the real Apple identifiers (and its own EAS project id) before its first build.
const VARIANTS = {
  christian: {
    name: 'Freely Spoken',
    iosBundleId: 'com.htsh.miccheck',
    androidPackage: 'com.htsh.miccheck',
    scheme: 'miccheck',
    icon: './assets/images/icon.png',
  },
  dhammapada: {
    name: 'Idle Ashes',
    iosBundleId: 'com.htsh.idleashes',
    androidPackage: 'com.htsh.idleashes',
    scheme: 'idleashes',
    // TODO: swap for a dedicated Idle Ashes icon/splash once designed.
    icon: './assets/images/icon.png',
  },
  stoic: {
    name: 'Freely Spoken (Stoic)',
    iosBundleId: 'com.htsh.miccheck.stoic',
    androidPackage: 'com.htsh.miccheck.stoic',
    scheme: 'miccheckstoic',
    icon: './assets/images/icon.png',
  },
};

function renameProduct(value, to) {
  return typeof value === 'string' ? value.split(BASE_NAME).join(to) : value;
}

module.exports = ({ config }) => {
  const variant = VARIANTS[appVariant] || VARIANTS.christian;

  // Native identity
  config.name = variant.name;
  config.scheme = variant.scheme;
  config.icon = variant.icon;
  config.ios = { ...(config.ios || {}), bundleIdentifier: variant.iosBundleId };
  config.android = { ...(config.android || {}), package: variant.androidPackage };

  // iOS Info.plist permission descriptions ("Allow Freely Spoken to ...")
  if (config.ios.infoPlist) {
    const infoPlist = { ...config.ios.infoPlist };
    for (const k of Object.keys(infoPlist)) {
      infoPlist[k] = renameProduct(infoPlist[k], variant.name);
    }
    config.ios.infoPlist = infoPlist;
  }

  // Config-plugin permission strings (expo-av, expo-speech-recognition)
  config.plugins = (config.plugins || []).map((plugin) => {
    if (!Array.isArray(plugin)) return plugin;
    const [name, options] = plugin;
    if (options && typeof options === 'object') {
      const next = { ...options };
      for (const k of Object.keys(next)) next[k] = renameProduct(next[k], variant.name);
      return [name, next];
    }
    return plugin;
  });

  // Inject EXPO_PUBLIC_* into extra and pin the resolved variant (replacing the
  // "$EXPO_PUBLIC_APP_VARIANT" placeholder from app.json).
  config.extra = {
    ...(config.extra || {}),
    lookupApiUrl,
    lookupClientSecret,
    appVariant,
  };

  return config;
};
