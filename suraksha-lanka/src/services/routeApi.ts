/**
 * Route Optimization API Service
 * Suraksha Lanka — Objective Multi-Hazard Routing Component
 *
 * Connects to the dedicated FastAPI service:
 *   GET  /health
 *   GET  /route/config
 *   GET  /locations/search
 *   GET  /locations/reverse
 *   POST /route/optimize
 *   POST /route/compare
 *   GET  /hazards/status
 *   POST /hazards/update
 */

import { API_BASE_URL } from "./disasterApi";
import { NativeModules } from "react-native";

export type RouteMethod =
  | "shortest_path"
  | "objective_weight"
  | "objective_fuzzy";

export type RouteRiskLevel = "low" | "moderate" | "high" | "critical";

export type RouteCoordinate = {
  latitude: number;
  longitude: number;
  label?: string | null;
};

export type SnappedPoint = RouteCoordinate & {
  node_id: string;
  road_distance_m: number;
};

export type HazardScores = {
  flood: number;
  landslide: number;
  elephant: number;
  buffalo: number;
  deer: number;
  wildboar: number;
};

export type RouteSegment = {
  sequence: number;
  road_name: string;
  distance_km: number;
  duration_min: number;
  risk_score: number;
  risk_level: RouteRiskLevel;
  hazards: HazardScores;
  start_coordinate_index: number;
  end_coordinate_index: number;
};

export type RiskSection = {
  risk_level: RouteRiskLevel;
  risk_score: number;
  coordinates: RouteCoordinate[];
};

export type RouteDetails = {
  algorithm: "a_star";
  method: RouteMethod;
  method_label: string;
  distance_km: number;
  duration_min: number;
  risk_score: number;
  risk_level: RouteRiskLevel;
  risk_exposure: number;
  maximum_segment_risk: number;
  requested_risk_aversion: number;
  effective_risk_aversion: number;
  detour_guardrail_pct: number;
  guardrail_applied: boolean;
  same_as_fastest: boolean;
  high_risk_segments: number;
  segment_count: number;
  risk_reduction_vs_fastest_pct: number;
  time_overhead_vs_fastest_pct: number;
  hazard_summary: HazardScores;
  coordinates: RouteCoordinate[];
  risk_sections: RiskSection[];
  segments: RouteSegment[];
};

export type MethodComparison = {
  method: RouteMethod;
  method_label: string;
  duration_min: number;
  distance_km: number;
  risk_score: number;
  risk_exposure: number;
  risk_level: RouteRiskLevel;
  high_risk_segments: number;
  risk_reduction_vs_fastest_pct: number;
  time_overhead_vs_fastest_pct: number;
  same_as_fastest: boolean;
};

export type LocationSuggestion = RouteCoordinate & {
  label: string;
  secondary_label: string;
  source: "catalog" | "road" | "reverse";
};

export type RouteDataQuality = {
  level: "high" | "moderate" | "limited";
  route_coverage_pct: number;
  grid_points: number;
  nominal_resolution_km: number;
  message: string;
  limitations: string[];
};

export type RouteModelEvidence = {
  model_name: string;
  weighting_method: "CRITIC";
  objective_weights: HazardScores;
  dataset_rows: number;
  dataset_sha256: string;
  monotonic_by_design: boolean;
  human_responses_required: boolean;
};

export type RouteOptimizeRequest = {
  origin: RouteCoordinate;
  destination: RouteCoordinate;
  method?: RouteMethod;
  risk_aversion?: number;
  max_detour_pct?: number;
  include_comparison?: boolean;
};

export type RouteOptimizeResponse = {
  route_id: string;
  status: "success";
  computed_at: string;
  processing_time_ms: number;
  origin: SnappedPoint;
  destination: SnappedPoint;
  network: {
    name: string;
    coverage: string;
    nodes: number;
    edges: number;
    source: "real" | "synthetic" | "custom";
    risk_cache_precomputed: boolean;
    hazard_version: number;
    live_update_count: number;
  };
  data_quality: RouteDataQuality;
  model: RouteModelEvidence;
  route: RouteDetails;
  comparison: MethodComparison[];
  recommendation: string;
};

export type RouteHealthResponse = {
  status: string;
  component: string;
  algorithm: string;
  decision_model: string;
  weighting_method: "CRITIC";
  methods: RouteMethod[];
  default_method: RouteMethod;
  default_risk_aversion: number;
  network: RouteOptimizeResponse["network"];
};

export type RouteConfigResponse = {
  coverage: string;
  bounds: { south: number; north: number; west: number; east: number };
  center: RouteCoordinate;
  methods: Record<RouteMethod, string>;
  default_method: RouteMethod;
  default_risk_aversion: number;
  objective_weighting: {
    method: "CRITIC";
    weights: HazardScores;
    contrast: HazardScores;
    information: HazardScores;
    row_count: number;
    dataset: string;
    dataset_sha256: string;
    formula: string;
  };
  model: RouteModelEvidence;
  hazard_grid: {
    bounds: { south: number; north: number; west: number; east: number };
    points: number;
    nominal_resolution_km: number;
  };
  suggested_locations: Array<RouteCoordinate & { label: string }>;
};

export type HazardStatusResponse = {
  hazard_version: number;
  live_update_count: number;
  last_update: null | {
    source: string;
    observed_at: string;
    received_at: string;
    coordinate: RouteCoordinate;
    radius_km: number;
    updated_edges: number;
    values: Partial<HazardScores>;
    hazard_version: number;
  };
  persistence: string;
  accepted_hazards: Array<keyof HazardScores>;
};

function inferRouteApiUrl(disasterApiUrl: string): string {
  const cleanUrl = disasterApiUrl.replace(/\/+$/, "");
  if (/:\d+$/.test(cleanUrl)) {
    return cleanUrl.replace(/:\d+$/, ":8001");
  }
  return cleanUrl + ":8001";
}

const configuredUrl = process.env.EXPO_PUBLIC_ROUTE_API_URL?.trim();

function inferMetroHostUrl(): string | null {
  const scriptUrl = (NativeModules as any)?.SourceCode?.scriptURL;
  if (typeof scriptUrl !== "string") {
    return null;
  }
  const match = /^https?:\/\/([^/:]+)/i.exec(scriptUrl);
  return match ? "http://" + match[1] + ":8001" : null;
}

export const ROUTE_API_BASE_URL =
  configuredUrl || inferMetroHostUrl() || inferRouteApiUrl(API_BASE_URL);

export class RouteApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "RouteApiError";
    this.status = status;
    this.code = code;
  }
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs = 120_000
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(ROUTE_API_BASE_URL + path, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      let payload: any = null;
      try {
        payload = await response.json();
      } catch {
        // The HTTP status below is still useful when no JSON body is returned.
      }
      const detail = payload?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : detail?.message || "Route API error: " + response.status;
      throw new RouteApiError(message, response.status, detail?.code);
    }

    return (await response.json()) as T;
  } catch (error: any) {
    if (error?.name === "AbortError") {
      throw new RouteApiError(
        "Route calculation timed out. Confirm the route API is running and try again.",
        408,
        "TIMEOUT"
      );
    }
    if (error instanceof RouteApiError) {
      throw error;
    }
    throw new RouteApiError(
      "Cannot connect to the route server. Check the API URL and Wi-Fi connection.",
      0,
      "NETWORK_ERROR"
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function getRouteHealth(): Promise<RouteHealthResponse> {
  return requestJson<RouteHealthResponse>("/health", { method: "GET" });
}

export async function getRouteConfig(): Promise<RouteConfigResponse> {
  return requestJson<RouteConfigResponse>("/route/config", { method: "GET" });
}

export async function getHazardStatus(): Promise<HazardStatusResponse> {
  return requestJson<HazardStatusResponse>("/hazards/status", { method: "GET" });
}

export async function searchLocations(
  query: string,
  limit = 8
): Promise<LocationSuggestion[]> {
  const params = new URLSearchParams({ q: query.trim(), limit: String(limit) });
  return requestJson<LocationSuggestion[]>(
    "/locations/search?" + params.toString(),
    { method: "GET" },
    15_000
  );
}

export async function reverseLocation(
  coordinate: RouteCoordinate
): Promise<LocationSuggestion> {
  const params = new URLSearchParams({
    latitude: String(coordinate.latitude),
    longitude: String(coordinate.longitude),
  });
  return requestJson<LocationSuggestion>(
    "/locations/reverse?" + params.toString(),
    { method: "GET" },
    15_000
  );
}

export async function optimizeRoute(
  input: RouteOptimizeRequest
): Promise<RouteOptimizeResponse> {
  return requestJson<RouteOptimizeResponse>("/route/optimize", {
    method: "POST",
    body: JSON.stringify({
      ...input,
      method: input.method || "objective_fuzzy",
      risk_aversion: input.risk_aversion ?? 8,
      max_detour_pct: input.max_detour_pct ?? 30,
      include_comparison: input.include_comparison ?? true,
    }),
  });
}

export async function compareRoutes(
  input: RouteOptimizeRequest
): Promise<RouteOptimizeResponse> {
  return requestJson<RouteOptimizeResponse>("/route/compare", {
    method: "POST",
    body: JSON.stringify({
      ...input,
      method: input.method || "objective_fuzzy",
      risk_aversion: input.risk_aversion ?? 8,
      max_detour_pct: input.max_detour_pct ?? 30,
      include_comparison: true,
    }),
  });
}

export function formatCoordinate(coordinate: RouteCoordinate): string {
  return (
    coordinate.latitude.toFixed(6) +
    ", " +
    coordinate.longitude.toFixed(6)
  );
}

export function getRouteRiskColor(level: RouteRiskLevel): string {
  switch (level) {
    case "low":
      return "#22C55E";
    case "moderate":
      return "#F59E0B";
    case "high":
      return "#F97316";
    case "critical":
      return "#DC2626";
    default:
      return "#64748B";
  }
}

export function getRouteRiskLabel(level: RouteRiskLevel): string {
  return level.charAt(0).toUpperCase() + level.slice(1);
}
