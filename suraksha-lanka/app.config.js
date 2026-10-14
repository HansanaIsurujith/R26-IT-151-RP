module.exports = ({ config }) => {
  const googleMapsApiKey = process.env.EXPO_PUBLIC_GOOGLE_MAPS_API_KEY;
  return {
    ...config,
    android: {
      ...config.android,
      ...(googleMapsApiKey
        ? { config: { googleMaps: { apiKey: googleMapsApiKey } } }
        : {}),
    },
  };
};
