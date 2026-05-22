const lookupApiUrl = process.env.EXPO_PUBLIC_LOOKUP_API_URL;
const lookupClientSecret = process.env.EXPO_PUBLIC_LOOKUP_CLIENT_SECRET;
const appVariant = process.env.EXPO_PUBLIC_APP_VARIANT || 'christian';

module.exports = ({ config }) => ({
  ...config,
  extra: {
    ...config.extra,
    lookupApiUrl,
    lookupClientSecret,
    appVariant,
  },
});
