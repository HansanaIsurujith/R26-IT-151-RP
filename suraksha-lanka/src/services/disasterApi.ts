/**
 * Disaster Prediction API Service
 * Suraksha Lanka — Risk Detection Component
 * Project: R26-IT-151 | Student: IT22294470
 *
 * Connects to FastAPI backend:
 *   GET /predict/flood/today
 *   GET /predict/flood/tomorrow
 *   GET /predict/landslide/today
 *   GET /predict/landslide/tomorrow
 *   POST /predict/flood/zones     (manual input)
 *   POST /predict/landslide/zones (manual input)
 *   GET /health
 */


// export const API_BASE_URL = "http://10.103.15.94:8000"; //my ip

export const API_BASE_URL = "http://localhost:8000";


// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────
export type RiskLevel = "high" | "warning" | "safe";

export type RiskZone = {
  lat:         number;
  lng:         number;
  probability: number;
  risk_level:  RiskLevel;
};

export type WeatherData = {
  rainfall_mm:    number;
  humidity_pct:   number;
  temperature_c:  number;
  wind_speed_kmh: number;
};

export type ZoneSummary = {
  total:   number;
  high:    number;
  warning: number;
  safe:    number;
};

export type ZoneResponse = {
  day:     string;        // "today" | "tomorrow" | "manual"
  zones:   RiskZone[];
  summary: ZoneSummary;
  weather: WeatherData;
};

export type ManualInput = {
  rainfall_mm:    number;
  humidity_pct:   number;
  temperature_c:  number;
  wind_speed_kmh: number;
};

// ─────────────────────────────────────────────
// Health Check
// ─────────────────────────────────────────────
export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────
// Flood Zones
// ─────────────────────────────────────────────

/** Fetch today's flood risk zones (auto weather from Open-Meteo) */
export async function getFloodZonesToday(): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/flood/today`, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Flood today error: ${res.status}`);
  return res.json();
}

/** Fetch tomorrow's flood risk zones (forecast) */
export async function getFloodZonesTomorrow(): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/flood/tomorrow`, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Flood tomorrow error: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
// Landslide Zones
// ─────────────────────────────────────────────

/** Fetch today's landslide risk zones */
export async function getLandslideZonesToday(): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/landslide/today`, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Landslide today error: ${res.status}`);
  return res.json();
}

/** Fetch tomorrow's landslide risk zones */
export async function getLandslideZonesTomorrow(): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/landslide/tomorrow`, {
    method:  "GET",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error(`Landslide tomorrow error: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
// Manual Input (Testing)
// ─────────────────────────────────────────────

export async function getFloodZonesManual(input: ManualInput): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/flood/zones`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Flood manual error: ${res.status}`);
  return res.json();
}

export async function getLandslideZonesManual(input: ManualInput): Promise<ZoneResponse> {
  const res = await fetch(`${API_BASE_URL}/predict/landslide/zones`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`Landslide manual error: ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
// UI Helpers
// ─────────────────────────────────────────────

/** Risk level → map circle color */
export function getRiskColor(riskLevel: RiskLevel): string {
  switch (riskLevel) {
    case "high":    return "#E53935"; // red
    case "warning": return "#FB8C00"; // orange
    case "safe":    return "#43A047"; // green
    default:        return "#9E9E9E"; // grey
  }
}

/** Risk level → circle fill color (with opacity) */
export function getRiskFillColor(riskLevel: RiskLevel): string {
  switch (riskLevel) {
    case "high":    return "rgba(229,57,53,0.25)";
    case "warning": return "rgba(251,140,0,0.2)";
    case "safe":    return "rgba(67,160,71,0.08)";
    default:        return "rgba(158,158,158,0.1)";
  }
}

/** Risk level → circle radius (meters) */
export function getRiskRadius(riskLevel: RiskLevel): number {
  switch (riskLevel) {
    case "high":    return 2500;
    case "warning": return 2000;
    case "safe":    return 1500;
    default:        return 1500;
  }
}

/** Disaster type → emoji */
export function getEventEmoji(type: "flood" | "landslide"): string {
  return type === "flood" ? "🌊" : "⛰️";
}

/** Filter zones — only high + warning for map display */
export function getVisibleZones(zones: RiskZone[]): RiskZone[] {
  return zones.filter(z => z.risk_level !== "safe");
}





// /**
//  * Disaster Prediction API Service
//  * React Native — connect to FastAPI backend
//  *
//  * Usage:
//  *   import { predictDisaster, predictBatch } from './disasterApi';
//  */

// // ─────────────────────────────────────────────
// // CONFIG — change this to your server IP/URL
// // ─────────────────────────────────────────────
// const API_BASE_URL = "http://10.26.3.24:8000"; 
// // Local testing:  "http://192.168.1.x:8000"  (ඔයාගේ PC IP එක)
// // Production:     "https://your-domain.com"

// // ─────────────────────────────────────────────
// // Types
// // ─────────────────────────────────────────────
// export type WeatherInput = {
//   rainfall:    number;  // mm
//   rain_3d:     number;  // mm cumulative 3 days
//   rain_7d:     number;  // mm cumulative 7 days
//   temperature: number;  // Celsius
//   humidity:    number;  // 0-100
//   latitude:    number;
//   longitude:   number;
//   elevation:   number;  // meters
//   date?:       string;  // "YYYY-MM-DD" — optional, defaults to today
// };

// export type PredictionResult = {
//   event:         string;   // "Flood" | "Landslide" | "Fog" | "Warning" | "No Risk"
//   event_label:   number;   // 0-4
//   confidence:    number;   // 0-100 percentage
//   risk_level:    string;   // "LOW" | "MEDIUM" | "MODERATE" | "HIGH"
//   message:       string;
//   probabilities: Record<string, number>;
// };

// export type BatchLocation = WeatherInput;

// export type BatchResult = {
//   count: number;
//   predictions: Array<{
//     latitude:   number;
//     longitude:  number;
//     event:      string;
//     risk_level: string;
//     confidence: number;
//     message:    string;
//   }>;
// };

// // ─────────────────────────────────────────────
// // API Calls
// // ─────────────────────────────────────────────

// /**
//  * Check if the API server is running
//  */
// export async function checkHealth(): Promise<boolean> {
//   try {
//     const res = await fetch(`${API_BASE_URL}/health`, {
//       method: "GET",
//       headers: { "Content-Type": "application/json" },
//     });
//     return res.ok;
//   } catch {
//     return false;
//   }
// }

// /**
//  * Predict disaster risk for a single location
//  *
//  * Example:
//  *   const result = await predictDisaster({
//  *     rainfall: 25, rain_3d: 80, rain_7d: 130,
//  *     temperature: 27.5, humidity: 85,
//  *     latitude: 6.9271, longitude: 79.8612,
//  *     elevation: 8
//  *   });
//  *   console.log(result.event);     // "Flood"
//  *   console.log(result.risk_level) // "HIGH"
//  */
// export async function predictDisaster(
//   input: WeatherInput
// ): Promise<PredictionResult> {
//   const res = await fetch(`${API_BASE_URL}/predict`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//     body:    JSON.stringify(input),
//   });

//   if (!res.ok) {
//     const err = await res.json();
//     throw new Error(err.detail || "Prediction failed");
//   }

//   return res.json();
// }

// /**
//  * Predict disaster risk for multiple locations (map grid)
//  * Max 100 locations per call
//  *
//  * Example:
//  *   const result = await predictBatch([
//  *     { rainfall: 25, rain_3d: 80, ...location1 },
//  *     { rainfall: 10, rain_3d: 30, ...location2 },
//  *   ]);
//  */
// export async function predictBatch(
//   locations: BatchLocation[]
// ): Promise<BatchResult> {
//   const res = await fetch(`${API_BASE_URL}/predict/batch`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//     body:    JSON.stringify({ locations }),
//   });

//   if (!res.ok) {
//     const err = await res.json();
//     throw new Error(err.detail || "Batch prediction failed");
//   }

//   return res.json();
// }

// // ─────────────────────────────────────────────
// // Helper: Risk level → color (for UI)
// // ─────────────────────────────────────────────
// export function getRiskColor(riskLevel: string): string {
//   switch (riskLevel) {
//     case "LOW":      return "#4CAF50"; // green
//     case "MODERATE": return "#FF9800"; // orange
//     case "MEDIUM":   return "#FF9800"; // orange
//     case "HIGH":     return "#F44336"; // red
//     default:         return "#9E9E9E"; // grey
//   }
// }

// export function getRiskEmoji(event: string): string {
//   switch (event) {
//     case "Flood":     return "🌊";
//     case "Landslide": return "⛰️";
//     case "Fog":       return "🌫️";
//     case "Warning":   return "⚠️";
//     case "No Risk":   return "✅";
//     default:          return "❓";
//   }
// }
