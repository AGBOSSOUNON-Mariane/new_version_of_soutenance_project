const { withAndroidManifest } = require('@expo/config-plugins');

const withClearTextTraffic = (config) => {
  return withAndroidManifest(config, (config) => {
    const androidManifest = config.modResults.manifest;

    // Trouver ou créer l'élément application
    if (!androidManifest.application) {
      androidManifest.application = [{}];
    }

    const application = androidManifest.application[0];

    // Ajouter usesCleartextTraffic
    application.$['android:usesCleartextTraffic'] = 'true';

    return config;
  });
};

module.exports = withClearTextTraffic;