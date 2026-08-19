/**
 * weatherService.js
 * Fetches real weather using Open-Meteo API (FREE — no API key needed)
 *
 * Location: services/weatherService.js
 */

const OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";

// ── Single location weather ────────────────────────────────
export async function getWeatherForLocation(latitude, longitude) {
  try {
    const url =
      `${OPEN_METEO_URL}?latitude=${latitude}&longitude=${longitude}` +
      `&current=temperature_2m,relative_humidity_2m,precipitation` +
      `&daily=precipitation_sum` +
      `&forecast_days=7` +
      `&timezone=Asia%2FColombo`;

    const res = await fetch(url);
    if (!res.ok) throw new Error("Weather API failed");

    const data    = await res.json();
    const current = data.current;
    const daily   = data.daily;

    const rain_3d = daily.precipitation_sum
      .slice(0, 3)
      .reduce((a, b) => a + (b || 0), 0);

    const rain_7d = daily.precipitation_sum
      .slice(0, 7)
      .reduce((a, b) => a + (b || 0), 0);

    return {
      latitude,
      longitude,
      rainfall:    parseFloat((current.precipitation        || 0).toFixed(2)),
      rain_3d:     parseFloat(rain_3d.toFixed(2)),
      rain_7d:     parseFloat(rain_7d.toFixed(2)),
      temperature: parseFloat((current.temperature_2m       || 27).toFixed(2)),
      humidity:    parseFloat((current.relative_humidity_2m || 75).toFixed(2)),
      elevation:   getElevationEstimate(latitude, longitude),
      date:        new Date().toISOString().split("T")[0].replace(/-/g, ""),
    };
  } catch (err) {
    console.warn("Weather fetch error:", err.message);
    return {
      latitude,
      longitude,
      rainfall:    0,
      rain_3d:     0,
      rain_7d:     0,
      temperature: 27,
      humidity:    75,
      elevation:   10,
      date:        new Date().toISOString().split("T")[0].replace(/-/g, ""),
    };
  }
}

// ── Grid weather (3x3 = 9 points around user) ─────────────
export async function getWeatherGrid(centerLat, centerLon, radius = 0.15, gridSize = 3) {
  const step   = (radius * 2) / (gridSize - 1);
  const points = [];

  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      points.push({
        lat: parseFloat((centerLat - radius + i * step).toFixed(5)),
        lon: parseFloat((centerLon - radius + j * step).toFixed(5)),
      });
    }
  }

  const results = await Promise.all(
    points.map(({ lat, lon }) => getWeatherForLocation(lat, lon))
  );

  return results;
}

// ── Elevation estimate for Sri Lanka ──────────────────────
function getElevationEstimate(lat, lon) {
  if (lon < 80.1 && lat < 7.2) return 5;
  if (lon < 80.3 && lat < 7.3) return 12;
  if (lon > 80.5)               return 45;
  return 10;
}
