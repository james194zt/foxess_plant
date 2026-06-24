/**
 * Fox Flow Scene — Lovelace card picker registration only.
 * Load after fox-flow-scene-card.js (defines the custom element first).
 */
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "fox-flow-scene-card")) {
  window.customCards.push({
    type: "fox-flow-scene-card",
    name: "Fox Flow Scene",
    description: "Live Fox ESS house energy flow scene (Fox Plant overview)",
    preview: false,
    documentationURL: "https://github.com/james194zt/foxess_plant",
    getEntitySuggestion: (hass, entityId) => {
      const domain = entityId.split(".")[0];
      if (domain !== "weather") return null;
      return {
        config: {
          type: "custom:fox-flow-scene-card",
          weather_entity: entityId,
          show_weather: true,
        },
      };
    },
  });
}
