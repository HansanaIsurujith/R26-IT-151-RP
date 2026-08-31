import { Platform } from "react-native";

const COMPUTER_IP = "127.0.0.1";
export const API_BASE_URL = Platform.OS === "web"
  ? "http://localhost:8000"
  : `http://${COMPUTER_IP}:8000`;

export type RiskLevel = "high" | "warning" | "safe";
export type RiskZone = {
  lat: number;
  lng: number;
  probability: number;
  flood_probability?: number;
  flood_risk?: boolean;
  risk_level: RiskLevel;
  today_rainfall_mm?: number;
  target_day_rainfall_mm?: number;
  rain_3d_mm?: number;
  rain_7d_mm?: number;
  rain_30d_mm?: number;
  elevation_m?: number;
  river_proximity_km?: number;
  weather_fallback?: boolean;
};
export type WeatherData = {
  rainfall_mm: number;
  humidity_pct?: number;
  temperature_c?: number;
  wind_speed_kmh?: number;
};
export type ZoneSummary = { total: number; high: number; warning: number; safe: number };
export type ZoneResponse = {
  day: string;
  date?: string;
  zones: RiskZone[];
  summary: ZoneSummary;
  weather?: WeatherData;
  weather_quality?: { fallback_points: number; total_points: number };
  confirmed_flood?: boolean;
  model_limitations?: string;
};
export type ManualInput = {
  rainfall_mm: number;
  humidity_pct: number;
  temperature_c: number;
  wind_speed_kmh: number;
};
export type DailyFloodPrediction = {
  latitude: number;
  longitude: number;
  date: string;
  day: "today" | "tomorrow";
  weather: {
    today_rainfall_mm: number;
    target_day_rainfall_mm: number;
    rain_3d_mm: number;
    rain_7d_mm: number;
    rain_30d_mm: number;
    humidity_pct: number;
    temperature_c: number;
    wind_speed_kmh: number;
  };
  terrain: { elevation_m: number; soil_type: number | string; river_proximity_km: number };
  flood_probability: number;
  flood_risk: boolean;
  risk_level: RiskLevel;
  confirmed_flood: boolean;
  data_source: string;
  model_limitations: string;
};

export async function getFloodZonesManual(
  input: ManualInput,
): Promise<ZoneResponse> {
  const response = await fetch(
    `${API_BASE_URL}/predict/flood/zones`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
    },
  );

  if (!response.ok) {
    const detail = await response.text();

    throw new Error(
      `Flood scenario error: ${response.status}: ${detail}`,
    );
  }

  return response.json();
}

async function getJson<T>(path: string, timeoutMs = 120000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`${response.status}: ${await response.text()}`);
    }
    return response.json();
  } finally {
    clearTimeout(timer);
  }
}

export async function checkHealth(): Promise<boolean> {
  try {
    await getJson("/health", 10000);
    return true;
  } catch {
    return false;
  }
}

function normalizeDailyZones(raw: any): ZoneResponse {
  const zones: RiskZone[] = (raw.zones ?? []).map((zone: any) => ({
    ...zone,
    probability: Number(zone.flood_probability ?? zone.probability ?? 0),
  }));
  const averageRain = zones.length
    ? zones.reduce((sum, zone) => sum + Number(zone.target_day_rainfall_mm ?? 0), 0) / zones.length
    : 0;
  return { ...raw, zones, weather: { rainfall_mm: Number(averageRain.toFixed(1)) } };
}

export async function getFloodZonesToday(): Promise<ZoneResponse> {
  return normalizeDailyZones(await getJson<any>("/predict/flood/daily/zones?day_offset=0"));
}
export async function getFloodZonesTomorrow(): Promise<ZoneResponse> {
  return normalizeDailyZones(await getJson<any>("/predict/flood/daily/zones?day_offset=1"));
}
export async function getDailyFloodRisk(latitude: number, longitude: number, dayOffset = 0): Promise<DailyFloodPrediction> {
  const query = `?latitude=${encodeURIComponent(latitude)}&longitude=${encodeURIComponent(longitude)}&day_offset=${dayOffset}`;
  return getJson<DailyFloodPrediction>(`/predict/flood/daily${query}`);
}
export async function getLandslideZonesToday(): Promise<ZoneResponse> {
  return getJson<ZoneResponse>("/predict/landslide/today");
}
export async function getLandslideZonesTomorrow(): Promise<ZoneResponse> {
  return getJson<ZoneResponse>("/predict/landslide/tomorrow");
}
export async function getLandslideZonesManual(input: ManualInput): Promise<ZoneResponse> {
  const response = await fetch(`${API_BASE_URL}/predict/landslide/zones`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(`Landslide manual error: ${response.status}`);
  return response.json();
}
export function getRiskColor(level: RiskLevel): string {
  return level === "high" ? "#E53935" : level === "warning" ? "#FB8C00" : "#43A047";
}
export function getRiskFillColor(level: RiskLevel): string {
  return level === "high" ? "rgba(229,57,53,0.25)" : level === "warning" ? "rgba(251,140,0,0.20)" : "rgba(67,160,71,0.08)";
}
export function getRiskRadius(level: RiskLevel): number {
  return level === "high" ? 2500 : level === "warning" ? 2000 : 1500;
}
export function getEventEmoji(type: "flood" | "landslide"): string {
  return type === "flood" ? "🌊" : "⛰️";
}
export function getVisibleZones(zones: RiskZone[] = []): RiskZone[] {
  return zones.filter((zone) => zone.risk_level !== "safe");
}
