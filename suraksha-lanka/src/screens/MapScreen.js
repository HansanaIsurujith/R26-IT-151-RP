/**
 * MapScreen.js
 * Suraksha Lanka — Risk Detection Component
 * Project: R26-IT-151 | Student: IT22294470
 *
 * Features:
 *  - Flood / Landslide zone circles on map
 *  - Today / Tomorrow toggle buttons
 *  - Auto fetch from FastAPI backend
 *  - Red / Orange / Green risk circles
 *  - Summary panel (high/warning/safe counts)
 */

import React, { useState, useEffect, useRef } from "react";
import {
  View, StyleSheet, Text, ActivityIndicator, ScrollView,
  Platform, Pressable, Alert, TouchableOpacity,
} from "react-native";
import * as Location from "expo-location";
import {
  evaluateWildlifeRisk,
  getWildlifeMapLocations,
  getFloodZonesToday,
  getFloodZonesTomorrow,
  getLandslideZonesToday,
  getLandslideZonesTomorrow,
  getRiskColor,
  getRiskFillColor,
  getRiskRadius,
  getVisibleZones,
} from "../services/disasterApi";

// ── Safely load maps ───────────────────────────────────────
let MapView         = null;
let Marker          = null;
let Circle          = null;
let PROVIDER_GOOGLE = null;
let mapModuleAvailable = false;

if (Platform.OS !== "web") {
  try {
    const M         = require("react-native-maps");
    MapView         = M.default || M;
    Marker          = M.Marker;
    Circle          = M.Circle;
    PROVIDER_GOOGLE = M.PROVIDER_GOOGLE;
    mapModuleAvailable = true;
  } catch (e) {
    console.warn("MapView not available:", e.message);
  }
}

// ── Config ─────────────────────────────────────────────────
const REFRESH_MS = 5 * 60 * 1000; // auto refresh every 5 mins
const WILDLIFE_MARKER_LATITUDE_DELTA_THRESHOLD = 1.0;
const MAX_WILDLIFE_MARKERS = 20;

// ── Gampaha center ─────────────────────────────────────────
const GAMPAHA_CENTER = { latitude: 7.08, longitude: 80.01 };

function getWildlifeRiskLabel(score) {
  if (score < 25) return "LOW";
  if (score < 50) return "MODERATE";
  if (score < 75) return "HIGH";
  return "VERY HIGH";
}

function getWildlifeRiskColour(score) {
  if (score < 25) return "#16A34A";
  if (score < 50) return "#EAB308";
  if (score < 75) return "#F97316";
  return "#DC2626";
}

function getWildlifeIcon(iconName, speciesName) {
  const icons = {
    elephant: "🐘",
    buffalo: "🦬",
    wild_boar: "🐗",
    spotted_deer: "🦌",
  };
  return icons[iconName] || speciesName?.charAt(0) || "🐾";
}

function getWildlifeLocationColour(riskColour) {
  if (riskColour === "RED") return "#DC2626";
  if (riskColour === "ORANGE") return "#F97316";
  if (riskColour === "YELLOW") return "#EAB308";
  return "#16A34A";
}

function getWildlifeLocationTitle(location) {
  const icon = getWildlifeIcon(location.primary_icon, location.primary_species);
  const additionalSpecies = location.additional_species_count > 0
    ? ` +${location.additional_species_count}`
    : "";
  return `${icon} ${location.primary_species}${additionalSpecies}`;
}

function getWildlifeRiskPriority(riskLevel) {
  if (riskLevel === "VERY HIGH") return 4;
  if (riskLevel === "HIGH") return 3;
  if (riskLevel === "MODERATE") return 2;
  return 1;
}

function selectWildlifeMarkers(locations, latitudeDelta = 1.0) {
  let markerLimit;

  if (latitudeDelta > 2.0) {
    markerLimit = 20;
  } else if (latitudeDelta > 1.0) {
    markerLimit = 50;
  } else if (latitudeDelta > 0.5) {
    markerLimit = 100;
  } else {
    markerLimit = MAX_WILDLIFE_MARKERS;
  }

  return [...locations]
    .sort((first, second) => (
      (Number(second.primary_score) || 0) - (Number(first.primary_score) || 0)
      || getWildlifeRiskPriority(second.risk_level) - getWildlifeRiskPriority(first.risk_level)
      || (Number(second.observation_count) || 0) - (Number(first.observation_count) || 0)
      || first.location_id.localeCompare(second.location_id)
    ))
    .slice(0, markerLimit);
}

// ════════════════════════════════════════════════════════════
export default function MapScreen({ route }) {
  const [userLocation,   setUserLocation]   = useState(null);
  const [isLoading,      setIsLoading]      = useState(true);
  const [wildlifeRisk, setWildlifeRisk] = useState(null);
  const [isLoadingWildlifeRisk, setIsLoadingWildlifeRisk] = useState(false);
  const [wildlifeRiskError, setWildlifeRiskError] = useState(null);
  const [wildlifeMapLocations, setWildlifeMapLocations] = useState([]);
  const [wildlifeZoomMessage, setWildlifeZoomMessage] = useState(false);
  const [selectedWildlifeLocation, setSelectedWildlifeLocation] = useState(null);

  // Mode state
  const [disasterType, setDisasterType] = useState(
    route?.params?.disasterType || "flood"
  );
  const [dayType, setDayType] = useState("today");
  const [isManual, setIsManual] = useState(false);

  // Zones
  const [zones,          setZones]          = useState([]);
  const [summary,        setSummary]        = useState(null);
  const [weather,        setWeather]        = useState(null);
  const [zonesLoading,   setZonesLoading]   = useState(false);
  const [lastFetched,    setLastFetched]    = useState(null);
  const [error,          setError]          = useState(null);

  const mapRef       = useRef(null);
  const refreshRef   = useRef(null);
  const wildlifeMapDebounceRef = useRef(null);
  const wildlifeMapRequestRef = useRef(0);

  // ── Handle manual zones from ManualInputScreen ────────────
  useEffect(() => {
    if (!route?.params?.manualZones) return;

    const {
      manualZones,
      manualSummary,
      manualWeather,
      disasterType: dt,
    } = route.params;

    setZones(getVisibleZones(manualZones));
    setSummary(manualSummary);
    setWeather(manualWeather);
    setDisasterType(dt || "flood");
    setLastFetched("Manual input");
    setIsManual(true);
    setIsLoading(false);
  }, [route?.params?.manualZones]);

  // ── Get GPS ───────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status === "granted") {
          const pos = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          });
          setUserLocation({
            latitude:  pos.coords.latitude,
            longitude: pos.coords.longitude,
          });
        } else {
          setUserLocation(GAMPAHA_CENTER);
        }
      } catch {
        setUserLocation(GAMPAHA_CENTER);
      } finally {
        setIsLoading(false);
      }
    })();

    return () => clearInterval(refreshRef.current);
  }, []);

  // ── Fetch wildlife risk after GPS is available ─────────────
  useEffect(() => {
    if (!userLocation) return;

    let isActive = true;

    const fetchWildlifeRisk = async () => {
      setIsLoadingWildlifeRisk(true);
      setWildlifeRiskError(null);

      try {
        const result = await evaluateWildlifeRisk(
          userLocation.latitude,
          userLocation.longitude
        );

        if (isActive) {
          setWildlifeRisk(result);
        }
      } catch (err) {
        if (isActive) {
          setWildlifeRiskError("Unable to calculate wildlife risk.");
          setWildlifeRisk(null);
        }
      } finally {
        if (isActive) {
          setIsLoadingWildlifeRisk(false);
        }
      }
    };

    fetchWildlifeRisk();

    return () => {
      isActive = false;
    };
  }, [userLocation]);

  // ── Fetch wildlife evidence locations for the visible map ──
  const handleMapRegionChangeComplete = (region) => {
    clearTimeout(wildlifeMapDebounceRef.current);


    setWildlifeZoomMessage(false);
    wildlifeMapDebounceRef.current = setTimeout(async () => {
      const requestId = wildlifeMapRequestRef.current + 1;
      wildlifeMapRequestRef.current = requestId;
      const bounds = {
        north: region.latitude + region.latitudeDelta / 2,
        south: region.latitude - region.latitudeDelta / 2,
        east: region.longitude + region.longitudeDelta / 2,
        west: region.longitude - region.longitudeDelta / 2,
      };

      try {
        const result = await getWildlifeMapLocations(
          bounds.north,
          bounds.south,
          bounds.east,
          bounds.west
        );

        if (requestId === wildlifeMapRequestRef.current) {
          setWildlifeMapLocations(selectWildlifeMarkers(result.locations));
          setSelectedWildlifeLocation(null);
        }
      } catch (err) {
        if (requestId === wildlifeMapRequestRef.current) {
          setWildlifeMapLocations([]);
          console.error("Wildlife map locations error:", err.message);
        }
      }
    }, 650);
  };

  useEffect(() => () => {
    clearTimeout(wildlifeMapDebounceRef.current);
  }, []);

  // ── Fetch zones when type or day changes ──────────────────
  useEffect(() => {
    // Do not overwrite manual simulation results
    if (isManual) {
      clearInterval(refreshRef.current);
      return;
    }

    fetchZones();

    // Auto refresh
    clearInterval(refreshRef.current);
    refreshRef.current = setInterval(fetchZones, REFRESH_MS);

    return () => clearInterval(refreshRef.current);
  }, [disasterType, dayType, isManual]);

  // ── Fetch from FastAPI ────────────────────────────────────
  const fetchZones = async () => {
    setZonesLoading(true);
    setError(null);
    try {
      let response;
      if (disasterType === "flood") {
        response = dayType === "today"
          ? await getFloodZonesToday()
          : await getFloodZonesTomorrow();
      } else {
        response = dayType === "today"
          ? await getLandslideZonesToday()
          : await getLandslideZonesTomorrow();
      }

      // Only show high + warning zones on map (safe zones too many)
      setZones(getVisibleZones(response.zones));
      setSummary(response.summary);
      setWeather(response.weather);
      setLastFetched(new Date().toLocaleTimeString());
    } catch (err) {
      setError("Backend connect වෙන්න බෑ. IP address check කරන්න.");
      console.error("Zone fetch error:", err.message);
    } finally {
      setZonesLoading(false);
    }
  };

  // ── Loading Screen ────────────────────────────────────────
  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0ea5e9" />
        <Text style={styles.loadingText}>Loading map...</Text>
      </View>
    );
  }

  // ── No Map Available ──────────────────────────────────────
  if (!mapModuleAvailable) {
    return (
      <View style={styles.placeholderMap}>
        <Text style={styles.title}>🗺️ Map not available</Text>
        <Text style={styles.subtitle}>Run on Android/iOS device</Text>
      </View>
    );
  }

  const floodActive     = disasterType === "flood";
  const landslideActive = disasterType === "landslide";
  const todayActive     = dayType === "today";
  const tomorrowActive  = dayType === "tomorrow";

  return (
    <View style={styles.container}>

      {/* ── Map ───────────────────────────────────────────── */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={{
          latitude:       7.70,
          longitude:      80.70,
          latitudeDelta:  3.0,
          longitudeDelta: 2.0,
        }}
        onRegionChangeComplete={handleMapRegionChangeComplete}
        showsUserLocation
        showsMyLocationButton
      >
        {/* Risk Zone Circles */}
        {zones.map((zone, idx) => (
          <Circle
            key={`zone-${idx}`}
            center={{ latitude: zone.lat, longitude: zone.lng }}
            radius={getRiskRadius(zone.risk_level)}
            strokeColor={getRiskColor(zone.risk_level)}
            fillColor={getRiskFillColor(zone.risk_level)}
            strokeWidth={1.5}
          />
        ))}

        {/* User Location Marker */}
        {userLocation && Marker && (
          <Marker
            coordinate={userLocation}
            title="You are here"
            pinColor="#0ea5e9"
          />
        )}

{/* Wildlife Evidence Location Markers */}
{Marker && wildlifeMapLocations.map((location) => (
  <Marker
    key={location.location_id}
    coordinate={{
      latitude: Number(location.latitude),
      longitude: Number(location.longitude),
    }}
    pinColor={getWildlifeLocationColour(location.risk_colour)}
    title={location.primary_species}
    onPress={() => setSelectedWildlifeLocation(location)}
  >
    <View
      style={{
        width: 50,
        height: 50,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Text
        style={{
          fontSize: 30,
          lineHeight: 36,
          textAlign: "center",
        }}
      >
        {getWildlifeIcon(
          location.primary_icon,
          location.primary_species
        )}
      </Text>

      {Number(location.additional_species_count) > 0 && (
        <View
          style={{
            position: "absolute",
            right: -5,
            top: -5,
            backgroundColor: "#000",
            borderRadius: 10,
            minWidth: 20,
            height: 20,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Text
            style={{
              color: "#fff",
              fontSize: 10,
              fontWeight: "bold",
            }}
          >
            +{location.additional_species_count}
          </Text>
        </View>
      )}
    </View>
  </Marker>
))}
      </MapView>

      {wildlifeZoomMessage && (
        <View style={styles.wildlifeZoomMessage}>
          <Text style={styles.wildlifeZoomMessageText}>Zoom in to view wildlife evidence</Text>
        </View>
      )}

      {/* Manual Mode Banner */}
      {isManual && (
        <View style={styles.manualBanner}>
          <Text style={styles.manualBannerText}>
            🧪 SIMULATION — {weather?.rainfall_mm}mm rainfall (not live weather)
          </Text>

          <TouchableOpacity
            onPress={() => {
              setIsManual(false);
              fetchZones();
            }}
          >
            <Text style={styles.manualBannerBtn}>Auto →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ── Disaster Type Buttons ─────────────────────────── */}
      {!isManual && (
        <View style={styles.typeButtonRow}>
          <TouchableOpacity
            style={[styles.typeBtn, floodActive && styles.typeBtnFloodActive]}
          onPress={() => setDisasterType("flood")}
        >
          <Text style={[styles.typeBtnText, floodActive && styles.typeBtnTextActive]}>
            🌊 Flood
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.typeBtn, landslideActive && styles.typeBtnLandslideActive]}
          onPress={() => setDisasterType("landslide")}
        >
          <Text style={[styles.typeBtnText, landslideActive && styles.typeBtnTextActive]}>
            ⛰️ Landslide
          </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ── Day Toggle Buttons ────────────────────────────── */}
      {!isManual && (
        <View style={styles.dayButtonRow}>
          <TouchableOpacity
          style={[styles.dayBtn, todayActive && styles.dayBtnActive]}
          onPress={() => setDayType("today")}
        >
          <Text style={[styles.dayBtnText, todayActive && styles.dayBtnTextActive]}>
            Today
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.dayBtn, tomorrowActive && styles.dayBtnActive]}
          onPress={() => setDayType("tomorrow")}
        >
          <Text style={[styles.dayBtnText, tomorrowActive && styles.dayBtnTextActive]}>
            Tomorrow
          </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ── Loading Bar ───────────────────────────────────── */}
      {zonesLoading && (
        <View style={styles.loadingBar}>
          <ActivityIndicator size="small" color="#fff" />
          <Text style={styles.loadingBarText}>
            Fetching {disasterType} zones ({dayType})...
          </Text>
        </View>
      )}

      {/* ── Error Bar ─────────────────────────────────────── */}
      {error && !zonesLoading && (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
          <TouchableOpacity onPress={fetchZones}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* ── Wildlife Risk Panel ───────────────────────────── */}
      {isLoadingWildlifeRisk && (
        <View style={styles.wildlifeStatusBar}>
          <ActivityIndicator size="small" color="#fff" />
          <Text style={styles.wildlifeStatusText}>Calculating wildlife risk...</Text>
        </View>
      )}

      {wildlifeRiskError && !isLoadingWildlifeRisk && (
        <View style={styles.wildlifeErrorBar}>
          <Text style={styles.wildlifeErrorText}>{wildlifeRiskError}</Text>
        </View>
      )}

      {wildlifeRisk && !isLoadingWildlifeRisk && (
        <View style={styles.wildlifePanel}>
          <View style={styles.wildlifeHeader}>
            <View>
              <Text style={styles.wildlifeTitle}>Wildlife Encounter Risk</Text>
              <Text style={styles.wildlifeScore}>
                {(Number(wildlifeRisk.encounter_risk_score) || 0).toFixed(1)} <Text style={styles.wildlifeScoreUnit}>/ 100</Text>
              </Text>
            </View>
            <View style={[styles.overallBadge, { backgroundColor: getWildlifeRiskColour(Number(wildlifeRisk.encounter_risk_score) || 0) }]}>
              <Text style={styles.overallBadgeText}>
                {getWildlifeRiskLabel(Number(wildlifeRisk.encounter_risk_score) || 0)}
              </Text>
              <Text style={styles.overallBadgeLabel}>RISK</Text>
            </View>
          </View>

          <Text style={styles.confidenceText}>
            Data confidence: {(Number(wildlifeRisk.data_confidence) || 0).toFixed(1)}%
          </Text>

          <ScrollView
            style={styles.speciesList}
            contentContainerStyle={styles.speciesListContent}
            showsVerticalScrollIndicator={false}
            nestedScrollEnabled
          >
            {[...wildlifeRisk.species]
              .sort((first, second) => (Number(second.score) || 0) - (Number(first.score) || 0))
              .map((animal) => {
                const animalScore = Number(animal.score) || 0;
                const animalColour = getWildlifeRiskColour(animalScore);

                return (
                  <View key={animal.species} style={styles.speciesCard}>
                    <View style={[styles.speciesRiskStripe, { backgroundColor: animalColour }]} />
                    <Text style={styles.speciesName} numberOfLines={1}>
                      {animal.icon} {animal.species}
                    </Text>
                    <Text style={styles.speciesScore}>{animalScore.toFixed(1)} / 100</Text>
                    <Text style={[styles.speciesRisk, { color: animalColour }]}>
                      {animal.risk_level}
                    </Text>
                    {animal.nearest_distance_km !== null && animal.nearest_distance_km !== undefined && (
                      <Text style={styles.speciesDistance}>
                        {Number(animal.nearest_distance_km).toFixed(3)} km
                      </Text>
                    )}
                  </View>
                );
              })}
          </ScrollView>
        </View>
      )}

      {selectedWildlifeLocation && (
        <View style={styles.selectedWildlifePanel}>
          <View style={styles.selectedWildlifeHeader}>
            <View>
              <Text style={styles.selectedWildlifeTitle}>Wildlife Evidence Location</Text>
              <Text style={styles.selectedWildlifePrimary}>
                {getWildlifeIcon(selectedWildlifeLocation.primary_icon, selectedWildlifeLocation.primary_species)} {selectedWildlifeLocation.primary_species}
              </Text>
            </View>
            <TouchableOpacity onPress={() => setSelectedWildlifeLocation(null)}>
              <Text style={styles.selectedWildlifeClose}>Close</Text>
            </TouchableOpacity>
          </View>
          <Text style={styles.selectedWildlifeMetric}>
            {selectedWildlifeLocation.risk_level} · Relative wildlife evidence score: {selectedWildlifeLocation.primary_score.toFixed(1)}
          </Text>
          <Text style={styles.selectedWildlifeMetric}>
            Observations: {selectedWildlifeLocation.observation_count}
          </Text>
          {selectedWildlifeLocation.species.map((animal) => (
            <Text key={animal.species} style={styles.selectedWildlifeSpecies}>
              {animal.species} — {animal.risk_level} — {animal.score.toFixed(1)}
              {animal.nearest_observation_distance_km !== null ? ` · ${animal.nearest_observation_distance_km.toFixed(3)} km` : ""}
            </Text>
          ))}
        </View>
      )}

      {/* ── Summary Panel ─────────────────────────────────── */}
      {summary && !zonesLoading && (
        <View style={styles.summaryPanel}>
          <Text style={styles.summaryTitle}>
            {floodActive ? "🌊 Flood Risk" : "⛰️ Landslide Risk"} — {dayType === "today" ? "Today" : "Tomorrow"}
          </Text>

          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <View style={[styles.summaryDot, { backgroundColor: "#E53935" }]} />
              <Text style={styles.summaryCount}>{summary.high}</Text>
              <Text style={styles.summaryLabel}>High</Text>
            </View>
            <View style={styles.summaryItem}>
              <View style={[styles.summaryDot, { backgroundColor: "#FB8C00" }]} />
              <Text style={styles.summaryCount}>{summary.warning}</Text>
              <Text style={styles.summaryLabel}>Warning</Text>
            </View>
            <View style={styles.summaryItem}>
              <View style={[styles.summaryDot, { backgroundColor: "#43A047" }]} />
              <Text style={styles.summaryCount}>{summary.safe}</Text>
              <Text style={styles.summaryLabel}>Safe</Text>
            </View>
          </View>

          {weather && (
            <Text style={styles.weatherText}>
              🌧️ {weather.rainfall_mm}mm  💧 {weather.humidity_pct}%  🌡️ {weather.temperature_c}°C
            </Text>
          )}

          {lastFetched && (
            <Text style={styles.updatedText}>Updated: {lastFetched}</Text>
          )}
        </View>
      )}

      {/* ── Legend ────────────────────────────────────────── */}
      <View style={styles.legend}>
        <View style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: "#E53935" }]} />
          <Text style={styles.legendText}>High Risk</Text>
        </View>
        <View style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: "#FB8C00" }]} />
          <Text style={styles.legendText}>Warning</Text>
        </View>
        <View style={styles.legendRow}>
          <View style={[styles.legendDot, { backgroundColor: "#43A047" }]} />
          <Text style={styles.legendText}>Safe</Text>
        </View>
      </View>

    </View>
  );
}

// ── Styles ─────────────────────────────────────────────────
const styles = StyleSheet.create({
  manualBanner: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    backgroundColor: "#7C3AED",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingVertical: 10,
    paddingHorizontal: 16,
    zIndex: 20,
  },

  manualBannerText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "600",
    flex: 1,
  },

  manualBannerBtn: {
    color: "#E9D5FF",
    fontSize: 13,
    fontWeight: "700",
    marginLeft: 10,
  },

  container:   { flex: 1, backgroundColor: "#f5f5f5" },
  map:         { flex: 1 },
  centered:    { flex: 1, alignItems: "center", justifyContent: "center" },
  loadingText: { marginTop: 10, color: "#555", fontSize: 14 },
  placeholderMap: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#e0f2fe" },
  title:       { fontSize: 24, fontWeight: "bold", textAlign: "center", color: "#0c4a6e" },
  subtitle:    { fontSize: 16, textAlign: "center", marginTop: 10, color: "#0369a1" },

  // Disaster type buttons
  typeButtonRow: {
    position: "absolute", top: 14, left: 16, right: 16,
    flexDirection: "row", gap: 10, zIndex: 10,
  },
  typeBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 14,
    backgroundColor: "#fff", alignItems: "center",
    elevation: 4, shadowColor: "#000", shadowOpacity: 0.12,
    shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
  },
  typeBtnFloodActive:     { backgroundColor: "#3b82f6" },
  typeBtnLandslideActive: { backgroundColor: "#ef4444" },
  typeBtnText:     { fontSize: 14, fontWeight: "600", color: "#64748b" },
  typeBtnTextActive: { color: "#fff" },

  // Day toggle
  dayButtonRow: {
    position: "absolute", top: 70, left: 16, right: 16,
    flexDirection: "row", gap: 10, zIndex: 10,
  },
  dayBtn: {
    flex: 1, paddingVertical: 8, borderRadius: 10,
    backgroundColor: "rgba(255,255,255,0.9)", alignItems: "center",
    elevation: 3, shadowColor: "#000", shadowOpacity: 0.1,
    shadowRadius: 4, shadowOffset: { width: 0, height: 1 },
  },
  dayBtnActive:    { backgroundColor: "#0ea5e9" },
  dayBtnText:      { fontSize: 13, fontWeight: "600", color: "#64748b" },
  dayBtnTextActive:{ color: "#fff" },

  // Loading / Error bars
  loadingBar: {
    position: "absolute", top: 120, left: 16, right: 16,
    backgroundColor: "#0EA5E9", borderRadius: 10,
    flexDirection: "row", alignItems: "center",
    paddingVertical: 10, paddingHorizontal: 16, gap: 10, elevation: 4,
  },
  loadingBarText: { color: "#fff", fontSize: 13, fontWeight: "600" },

  errorBar: {
    position: "absolute", top: 120, left: 16, right: 16,
    backgroundColor: "#FEF2F2", borderRadius: 10, borderWidth: 1,
    borderColor: "#FECACA", flexDirection: "row", alignItems: "center",
    justifyContent: "space-between", paddingVertical: 10, paddingHorizontal: 16,
  },
  errorText:  { fontSize: 12, color: "#DC2626", flex: 1 },
  retryText:  { fontSize: 12, color: "#0ea5e9", fontWeight: "700", marginLeft: 8 },

  // Wildlife status and results
  wildlifeStatusBar: {
    position: "absolute", top: 150, left: 16, right: 16,
    backgroundColor: "#0EA5E9", borderRadius: 10,
    paddingVertical: 10, paddingHorizontal: 16,
    flexDirection: "row", alignItems: "center", gap: 10,
    elevation: 4,
  },
  wildlifeStatusText: { color: "#fff", fontSize: 13, fontWeight: "600" },
  wildlifeErrorBar: {
    position: "absolute", top: 150, left: 16, right: 16,
    backgroundColor: "#FEF2F2", borderRadius: 10,
    borderWidth: 1, borderColor: "#FECACA",
    paddingVertical: 10, paddingHorizontal: 16,
    elevation: 4,
  },
  wildlifeErrorText: { color: "#DC2626", fontSize: 12, fontWeight: "600" },
  wildlifeZoomMessage: {
    position: "absolute", top: 150, left: 16, right: 16,
    backgroundColor: "rgba(15,23,42,0.82)", borderRadius: 10,
    paddingVertical: 10, paddingHorizontal: 16, elevation: 4,
  },
  wildlifeZoomMessageText: { color: "#fff", fontSize: 12, fontWeight: "600" },
  wildlifePanel: {
    position: "absolute", bottom: 16, left: 16, right: 16,
    maxHeight: "42%", backgroundColor: "rgba(255,255,255,0.97)",
    borderRadius: 16, padding: 14, elevation: 6,
    shadowColor: "#000", shadowOpacity: 0.15,
    shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
  },
  wildlifeHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  wildlifeTitle: { fontSize: 14, fontWeight: "700", color: "#0F172A", marginBottom: 4 },
  wildlifeScore: { fontSize: 28, fontWeight: "800", color: "#0F172A" },
  wildlifeScoreUnit: { fontSize: 14, fontWeight: "600", color: "#64748B" },
  overallBadge: { minWidth: 86, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 10, alignItems: "center" },
  overallBadgeText: { color: "#fff", fontSize: 12, fontWeight: "800", textAlign: "center" },
  overallBadgeLabel: { color: "rgba(255,255,255,0.85)", fontSize: 9, fontWeight: "700", marginTop: 2 },
  confidenceText: { fontSize: 11, color: "#64748B", marginTop: 4, marginBottom: 8 },
  speciesList: { flexGrow: 0 },
  speciesListContent: { paddingBottom: 2 },
  speciesCard: {
    minHeight: 42, borderTopWidth: 1, borderTopColor: "#E2E8F0",
    paddingVertical: 7, paddingLeft: 10, flexDirection: "row", alignItems: "center", gap: 8,
  },
  speciesRiskStripe: { width: 4, height: 28, borderRadius: 2 },
  speciesName: { flex: 1, fontSize: 12, fontWeight: "700", color: "#0F172A" },
  speciesRisk: { fontSize: 11, fontWeight: "800" },
  speciesScore: { width: 58, fontSize: 11, color: "#475569", textAlign: "right" },
  speciesDistance: { fontSize: 11, color: "#64748B" },
 wildlifeMarker: {
  width: 52,
  height: 52,
  borderRadius: 26,
  borderWidth: 3,
  backgroundColor: "#FFFFFF",
  alignItems: "center",
  justifyContent: "center",
  elevation: 8,
},

wildlifeMarkerIcon: {
  fontSize: 28,
  lineHeight: 34,
  textAlign: "center",
  includeFontPadding: false,
},

wildlifeMarkerCount: {
  position: "absolute",
  right: -10,
  top: -8,
  minWidth: 22,
  height: 20,
  borderRadius: 10,
  backgroundColor: "#0F172A",
  alignItems: "center",
  justifyContent: "center",
  paddingHorizontal: 4,
},

wildlifeMarkerCountText: {
  color: "#FFFFFF",
  fontSize: 10,
  fontWeight: "800",
  textAlign: "center",
},
  selectedWildlifePanel: {
    position: "absolute", left: 16, right: 16, bottom: "44%",
    backgroundColor: "rgba(255,255,255,0.98)", borderRadius: 14,
    padding: 12, elevation: 7,
    shadowColor: "#000", shadowOpacity: 0.18,
    shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
  },
  selectedWildlifeHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  selectedWildlifeTitle: { fontSize: 12, color: "#64748B", fontWeight: "600" },
  selectedWildlifePrimary: { fontSize: 16, color: "#0F172A", fontWeight: "800", marginTop: 3 },
  selectedWildlifeClose: { color: "#0EA5E9", fontSize: 11, fontWeight: "700" },
  selectedWildlifeMetric: { color: "#334155", fontSize: 11, marginTop: 5 },
  selectedWildlifeSpecies: { color: "#475569", fontSize: 11, marginTop: 4 },

  // Summary panel
  summaryPanel: {
    position: "absolute", bottom: 220, left: 16, right: 16,
    backgroundColor: "rgba(255,255,255,0.96)", borderRadius: 16,
    padding: 14, elevation: 6,
    shadowColor: "#000", shadowOpacity: 0.15,
    shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
  },
  summaryTitle: { fontSize: 14, fontWeight: "700", color: "#0F172A", marginBottom: 10 },
  summaryRow:   { flexDirection: "row", justifyContent: "space-around", marginBottom: 8 },
  summaryItem:  { alignItems: "center", gap: 4 },
  summaryDot:   { width: 12, height: 12, borderRadius: 6 },
  summaryCount: { fontSize: 20, fontWeight: "800", color: "#0F172A" },
  summaryLabel: { fontSize: 11, color: "#64748B" },
  weatherText:  { fontSize: 12, color: "#475569", textAlign: "center", marginTop: 4 },
  updatedText:  { fontSize: 10, color: "#94A3B8", textAlign: "center", marginTop: 4 },

  // Legend
  legend: {
    position: "absolute", bottom: 170, right: 16,
    backgroundColor: "rgba(255,255,255,0.95)", borderRadius: 12,
    padding: 10, elevation: 4, gap: 6,
    shadowColor: "#000", shadowOpacity: 0.1,
    shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
  },
  legendRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText:{ fontSize: 11, color: "#333" },
});
