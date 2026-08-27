// /**
//  * MapScreen.js
//  * Suraksha Lanka — Risk Detection Component
//  * Project: R26-IT-151 | Student: IT22294470
//  *
//  * Features:
//  *  - Flood / Landslide zone circles on map
//  *  - Today / Tomorrow toggle buttons
//  *  - Auto fetch from FastAPI backend
//  *  - Red / Orange / Green risk circles
//  *  - Summary panel (high/warning/safe counts)
//  */

// import React, { useState, useEffect, useRef } from "react";
// import {
//   View, StyleSheet, Text, ActivityIndicator,
//   Platform, Pressable, Alert, TouchableOpacity,
// } from "react-native";
// import * as Location from "expo-location";
// import {
//   getFloodZonesToday,
//   getFloodZonesTomorrow,
//   getLandslideZonesToday,
//   getLandslideZonesTomorrow,
//   getRiskColor,
//   getRiskFillColor,
//   getRiskRadius,
//   getVisibleZones,
// } from "../services/disasterApi";

// // ── Safely load maps ───────────────────────────────────────
// let MapView         = null;
// let Marker          = null;
// let Circle          = null;
// let PROVIDER_GOOGLE = null;
// let mapModuleAvailable = false;

// if (Platform.OS !== "web") {
//   try {
//     const M         = require("react-native-maps");
//     MapView         = M.default || M;
//     Marker          = M.Marker;
//     Circle          = M.Circle;
//     PROVIDER_GOOGLE = M.PROVIDER_GOOGLE;
//     mapModuleAvailable = true;
//   } catch (e) {
//     console.warn("MapView not available:", e.message);
//   }
// }

// // ── Config ─────────────────────────────────────────────────
// const REFRESH_MS = 5 * 60 * 1000; // auto refresh every 5 mins

// // ── Gampaha center ─────────────────────────────────────────
// const GAMPAHA_CENTER = { latitude: 7.08, longitude: 80.01 };

// // ════════════════════════════════════════════════════════════
// export default function MapScreen() {
//   const [userLocation,   setUserLocation]   = useState(null);
//   const [isLoading,      setIsLoading]      = useState(true);

//   // Mode state
//   const [disasterType,   setDisasterType]   = useState("flood");     // "flood" | "landslide"
//   const [dayType,        setDayType]        = useState("today");      // "today" | "tomorrow"

//   // Zones
//   const [zones,          setZones]          = useState([]);
//   const [summary,        setSummary]        = useState(null);
//   const [weather,        setWeather]        = useState(null);
//   const [zonesLoading,   setZonesLoading]   = useState(false);
//   const [lastFetched,    setLastFetched]    = useState(null);
//   const [error,          setError]          = useState(null);

//   const mapRef       = useRef(null);
//   const refreshRef   = useRef(null);

//   // ── Get GPS ───────────────────────────────────────────────
//   useEffect(() => {
//     (async () => {
//       try {
//         const { status } = await Location.requestForegroundPermissionsAsync();
//         if (status === "granted") {
//           const pos = await Location.getCurrentPositionAsync({
//             accuracy: Location.Accuracy.Balanced,
//           });
//           setUserLocation({
//             latitude:  pos.coords.latitude,
//             longitude: pos.coords.longitude,
//           });
//         } else {
//           setUserLocation(GAMPAHA_CENTER);
//         }
//       } catch {
//         setUserLocation(GAMPAHA_CENTER);
//       } finally {
//         setIsLoading(false);
//       }
//     })();

//     return () => clearInterval(refreshRef.current);
//   }, []);

//   // ── Fetch zones when type or day changes ──────────────────
//   useEffect(() => {
//     fetchZones();

//     // Auto refresh
//     clearInterval(refreshRef.current);
//     refreshRef.current = setInterval(fetchZones, REFRESH_MS);
//     return () => clearInterval(refreshRef.current);
//   }, [disasterType, dayType]);

//   // ── Fetch from FastAPI ────────────────────────────────────
//   const fetchZones = async () => {
//     setZonesLoading(true);
//     setError(null);
//     try {
//       let response;
//       if (disasterType === "flood") {
//         response = dayType === "today"
//           ? await getFloodZonesToday()
//           : await getFloodZonesTomorrow();
//       } else {
//         response = dayType === "today"
//           ? await getLandslideZonesToday()
//           : await getLandslideZonesTomorrow();
//       }

//       // Only show high + warning zones on map (safe zones too many)
//       setZones(getVisibleZones(response.zones));
//       setSummary(response.summary);
//       setWeather(response.weather);
//       setLastFetched(new Date().toLocaleTimeString());
//     } catch (err) {
//       setError("Backend connect වෙන්න බෑ. IP address check කරන්න.");
//       console.error("Zone fetch error:", err.message);
//     } finally {
//       setZonesLoading(false);
//     }
//   };

//   // ── Loading Screen ────────────────────────────────────────
//   if (isLoading) {
//     return (
//       <View style={styles.centered}>
//         <ActivityIndicator size="large" color="#0ea5e9" />
//         <Text style={styles.loadingText}>Loading map...</Text>
//       </View>
//     );
//   }

//   // ── No Map Available ──────────────────────────────────────
//   if (!mapModuleAvailable) {
//     return (
//       <View style={styles.placeholderMap}>
//         <Text style={styles.title}>🗺️ Map not available</Text>
//         <Text style={styles.subtitle}>Run on Android/iOS device</Text>
//       </View>
//     );
//   }

//   const floodActive     = disasterType === "flood";
//   const landslideActive = disasterType === "landslide";
//   const todayActive     = dayType === "today";
//   const tomorrowActive  = dayType === "tomorrow";

//   return (
//     <View style={styles.container}>

//       {/* ── Map ───────────────────────────────────────────── */}
//       <MapView
//         ref={mapRef}
//         style={styles.map}
//         provider={PROVIDER_GOOGLE}
//         initialRegion={{
//           latitude:       userLocation?.latitude  || GAMPAHA_CENTER.latitude,
//           longitude:      userLocation?.longitude || GAMPAHA_CENTER.longitude,
//           latitudeDelta:  0.5,
//           longitudeDelta: 0.5,
//         }}
//         showsUserLocation
//         showsMyLocationButton
//       >
//         {/* Risk Zone Circles */}
//         {zones.map((zone, idx) => (
//           <Circle
//             key={`zone-${idx}`}
//             center={{ latitude: zone.lat, longitude: zone.lng }}
//             radius={getRiskRadius(zone.risk_level)}
//             strokeColor={getRiskColor(zone.risk_level)}
//             fillColor={getRiskFillColor(zone.risk_level)}
//             strokeWidth={1.5}
//           />
//         ))}

//         {/* User Location Marker */}
//         {userLocation && Marker && (
//           <Marker
//             coordinate={userLocation}
//             title="You are here"
//             pinColor="#0ea5e9"
//           />
//         )}
//       </MapView>

//       {/* ── Disaster Type Buttons ─────────────────────────── */}
//       <View style={styles.typeButtonRow}>
//         <TouchableOpacity
//           style={[styles.typeBtn, floodActive && styles.typeBtnFloodActive]}
//           onPress={() => setDisasterType("flood")}
//         >
//           <Text style={[styles.typeBtnText, floodActive && styles.typeBtnTextActive]}>
//             🌊 Flood
//           </Text>
//         </TouchableOpacity>

//         <TouchableOpacity
//           style={[styles.typeBtn, landslideActive && styles.typeBtnLandslideActive]}
//           onPress={() => setDisasterType("landslide")}
//         >
//           <Text style={[styles.typeBtnText, landslideActive && styles.typeBtnTextActive]}>
//             ⛰️ Landslide
//           </Text>
//         </TouchableOpacity>
//       </View>

//       {/* ── Day Toggle Buttons ────────────────────────────── */}
//       <View style={styles.dayButtonRow}>
//         <TouchableOpacity
//           style={[styles.dayBtn, todayActive && styles.dayBtnActive]}
//           onPress={() => setDayType("today")}
//         >
//           <Text style={[styles.dayBtnText, todayActive && styles.dayBtnTextActive]}>
//             Today
//           </Text>
//         </TouchableOpacity>

//         <TouchableOpacity
//           style={[styles.dayBtn, tomorrowActive && styles.dayBtnActive]}
//           onPress={() => setDayType("tomorrow")}
//         >
//           <Text style={[styles.dayBtnText, tomorrowActive && styles.dayBtnTextActive]}>
//             Tomorrow
//           </Text>
//         </TouchableOpacity>
//       </View>

//       {/* ── Loading Bar ───────────────────────────────────── */}
//       {zonesLoading && (
//         <View style={styles.loadingBar}>
//           <ActivityIndicator size="small" color="#fff" />
//           <Text style={styles.loadingBarText}>
//             Fetching {disasterType} zones ({dayType})...
//           </Text>
//         </View>
//       )}

//       {/* ── Error Bar ─────────────────────────────────────── */}
//       {error && !zonesLoading && (
//         <View style={styles.errorBar}>
//           <Text style={styles.errorText}>⚠️ {error}</Text>
//           <TouchableOpacity onPress={fetchZones}>
//             <Text style={styles.retryText}>Retry</Text>
//           </TouchableOpacity>
//         </View>
//       )}

//       {/* ── Summary Panel ─────────────────────────────────── */}
//       {summary && !zonesLoading && (
//         <View style={styles.summaryPanel}>
//           <Text style={styles.summaryTitle}>
//             {floodActive ? "🌊 Flood Risk" : "⛰️ Landslide Risk"} — {dayType === "today" ? "Today" : "Tomorrow"}
//           </Text>

//           <View style={styles.summaryRow}>
//             <View style={styles.summaryItem}>
//               <View style={[styles.summaryDot, { backgroundColor: "#E53935" }]} />
//               <Text style={styles.summaryCount}>{summary.high}</Text>
//               <Text style={styles.summaryLabel}>High</Text>
//             </View>
//             <View style={styles.summaryItem}>
//               <View style={[styles.summaryDot, { backgroundColor: "#FB8C00" }]} />
//               <Text style={styles.summaryCount}>{summary.warning}</Text>
//               <Text style={styles.summaryLabel}>Warning</Text>
//             </View>
//             <View style={styles.summaryItem}>
//               <View style={[styles.summaryDot, { backgroundColor: "#43A047" }]} />
//               <Text style={styles.summaryCount}>{summary.safe}</Text>
//               <Text style={styles.summaryLabel}>Safe</Text>
//             </View>
//           </View>

//           {weather && (
//             <Text style={styles.weatherText}>
//               🌧️ {weather.rainfall_mm}mm  💧 {weather.humidity_pct}%  🌡️ {weather.temperature_c}°C
//             </Text>
//           )}

//           {lastFetched && (
//             <Text style={styles.updatedText}>Updated: {lastFetched}</Text>
//           )}
//         </View>
//       )}

//       {/* ── Legend ────────────────────────────────────────── */}
//       <View style={styles.legend}>
//         <View style={styles.legendRow}>
//           <View style={[styles.legendDot, { backgroundColor: "#E53935" }]} />
//           <Text style={styles.legendText}>High Risk</Text>
//         </View>
//         <View style={styles.legendRow}>
//           <View style={[styles.legendDot, { backgroundColor: "#FB8C00" }]} />
//           <Text style={styles.legendText}>Warning</Text>
//         </View>
//         <View style={styles.legendRow}>
//           <View style={[styles.legendDot, { backgroundColor: "#43A047" }]} />
//           <Text style={styles.legendText}>Safe</Text>
//         </View>
//       </View>

//     </View>
//   );
// }

// // ── Styles ─────────────────────────────────────────────────
// const styles = StyleSheet.create({
//   container:   { flex: 1, backgroundColor: "#f5f5f5" },
//   map:         { flex: 1 },
//   centered:    { flex: 1, alignItems: "center", justifyContent: "center" },
//   loadingText: { marginTop: 10, color: "#555", fontSize: 14 },
//   placeholderMap: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#e0f2fe" },
//   title:       { fontSize: 24, fontWeight: "bold", textAlign: "center", color: "#0c4a6e" },
//   subtitle:    { fontSize: 16, textAlign: "center", marginTop: 10, color: "#0369a1" },

//   // Disaster type buttons
//   typeButtonRow: {
//     position: "absolute", top: 14, left: 16, right: 16,
//     flexDirection: "row", gap: 10, zIndex: 10,
//   },
//   typeBtn: {
//     flex: 1, paddingVertical: 12, borderRadius: 14,
//     backgroundColor: "#fff", alignItems: "center",
//     elevation: 4, shadowColor: "#000", shadowOpacity: 0.12,
//     shadowRadius: 6, shadowOffset: { width: 0, height: 2 },
//   },
//   typeBtnFloodActive:     { backgroundColor: "#3b82f6" },
//   typeBtnLandslideActive: { backgroundColor: "#ef4444" },
//   typeBtnText:     { fontSize: 14, fontWeight: "600", color: "#64748b" },
//   typeBtnTextActive: { color: "#fff" },

//   // Day toggle
//   dayButtonRow: {
//     position: "absolute", top: 70, left: 16, right: 16,
//     flexDirection: "row", gap: 10, zIndex: 10,
//   },
//   dayBtn: {
//     flex: 1, paddingVertical: 8, borderRadius: 10,
//     backgroundColor: "rgba(255,255,255,0.9)", alignItems: "center",
//     elevation: 3, shadowColor: "#000", shadowOpacity: 0.1,
//     shadowRadius: 4, shadowOffset: { width: 0, height: 1 },
//   },
//   dayBtnActive:    { backgroundColor: "#0ea5e9" },
//   dayBtnText:      { fontSize: 13, fontWeight: "600", color: "#64748b" },
//   dayBtnTextActive:{ color: "#fff" },

//   // Loading / Error bars
//   loadingBar: {
//     position: "absolute", top: 120, left: 16, right: 16,
//     backgroundColor: "#0EA5E9", borderRadius: 10,
//     flexDirection: "row", alignItems: "center",
//     paddingVertical: 10, paddingHorizontal: 16, gap: 10, elevation: 4,
//   },
//   loadingBarText: { color: "#fff", fontSize: 13, fontWeight: "600" },

//   errorBar: {
//     position: "absolute", top: 120, left: 16, right: 16,
//     backgroundColor: "#FEF2F2", borderRadius: 10, borderWidth: 1,
//     borderColor: "#FECACA", flexDirection: "row", alignItems: "center",
//     justifyContent: "space-between", paddingVertical: 10, paddingHorizontal: 16,
//   },
//   errorText:  { fontSize: 12, color: "#DC2626", flex: 1 },
//   retryText:  { fontSize: 12, color: "#0ea5e9", fontWeight: "700", marginLeft: 8 },

//   // Summary panel
//   summaryPanel: {
//     position: "absolute", bottom: 20, left: 16, right: 16,
//     backgroundColor: "rgba(255,255,255,0.96)", borderRadius: 16,
//     padding: 14, elevation: 6,
//     shadowColor: "#000", shadowOpacity: 0.15,
//     shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
//   },
//   summaryTitle: { fontSize: 14, fontWeight: "700", color: "#0F172A", marginBottom: 10 },
//   summaryRow:   { flexDirection: "row", justifyContent: "space-around", marginBottom: 8 },
//   summaryItem:  { alignItems: "center", gap: 4 },
//   summaryDot:   { width: 12, height: 12, borderRadius: 6 },
//   summaryCount: { fontSize: 20, fontWeight: "800", color: "#0F172A" },
//   summaryLabel: { fontSize: 11, color: "#64748B" },
//   weatherText:  { fontSize: 12, color: "#475569", textAlign: "center", marginTop: 4 },
//   updatedText:  { fontSize: 10, color: "#94A3B8", textAlign: "center", marginTop: 4 },

//   // Legend
//   legend: {
//     position: "absolute", bottom: 170, right: 16,
//     backgroundColor: "rgba(255,255,255,0.95)", borderRadius: 12,
//     padding: 10, elevation: 4, gap: 6,
//     shadowColor: "#000", shadowOpacity: 0.1,
//     shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
//   },
//   legendRow: { flexDirection: "row", alignItems: "center", gap: 6 },
//   legendDot: { width: 10, height: 10, borderRadius: 5 },
//   legendText:{ fontSize: 11, color: "#333" },
// });

/**
 * MapScreen.js - FIXED v2
 * Suraksha Lanka — Risk Detection Component
 * Project: R26-IT-151 | Student: IT22294470
 */

import React, { useState, useEffect, useRef } from "react";
import {
  View, StyleSheet, Text, ActivityIndicator,
  Platform, TouchableOpacity,
} from "react-native";
import * as Location from "expo-location";
import {
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

const REFRESH_MS    = 5 * 60 * 1000;
const GAMPAHA_CENTER = { latitude: 7.08, longitude: 80.01 };

export default function MapScreen({ route }) {
  const [userLocation,  setUserLocation]  = useState(null);
  const [isLoading,     setIsLoading]     = useState(true);
  const [disasterType,  setDisasterType]  = useState(
    route?.params?.disasterType || "flood"
  );
  const [dayType,       setDayType]       = useState("today");
  const [zones,         setZones]         = useState([]);
  const [summary,       setSummary]       = useState(null);
  const [weather,       setWeather]       = useState(null);
  const [zonesLoading,  setZonesLoading]  = useState(false);
  const [lastFetched,   setLastFetched]   = useState(null);
  const [error,         setError]         = useState(null);
  const [isManual,      setIsManual]      = useState(false);

  const mapRef     = useRef(null);
  const refreshRef = useRef(null);

  // ── Handle manual zones from ManualInputScreen ────────────
  useEffect(() => {
    if (route?.params?.manualZones) {
      const { manualZones, manualSummary, manualWeather, disasterType: dt } = route.params;
      setZones(getVisibleZones(manualZones));
      setSummary(manualSummary);
      setWeather(manualWeather);
      setDisasterType(dt || "flood");
      setLastFetched("Manual input");
      setIsManual(true);
      setIsLoading(false);
    }
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
        if (!route?.params?.manualZones) setIsLoading(false);
      }
    })();
    return () => clearInterval(refreshRef.current);
  }, []);

  // ── Auto fetch when type/day changes ─────────────────────
  useEffect(() => {
    if (!route?.params?.manualZones || !isManual) {
      setIsManual(false);
      fetchZones();
      clearInterval(refreshRef.current);
      refreshRef.current = setInterval(fetchZones, REFRESH_MS);
    }
    return () => clearInterval(refreshRef.current);
  }, [disasterType, dayType]);

  // ── Fetch from FastAPI ────────────────────────────────────
  const fetchZones = async () => {
    setZonesLoading(true);
    setError(null);
    setIsManual(false);
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
      setZones(getVisibleZones(response.zones));
      setSummary(response.summary);
      setWeather(response.weather);
      setLastFetched(new Date().toLocaleTimeString());
    } catch (err) {
      setError("Backend connect වෙන්න බෑ.");
    } finally {
      setZonesLoading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#0ea5e9" />
        <Text style={styles.loadingText}>Loading map...</Text>
      </View>
    );
  }

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

      {/* Map */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={{
          latitude:      userLocation?.latitude  || GAMPAHA_CENTER.latitude,
          longitude:     userLocation?.longitude || GAMPAHA_CENTER.longitude,
          latitudeDelta:  0.5,
          longitudeDelta: 0.5,
        }}
        showsUserLocation
        showsMyLocationButton
      >
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
        {userLocation && Marker && (
          <Marker
            coordinate={userLocation}
            title="You are here"
            pinColor="#0ea5e9"
          />
        )}
      </MapView>

      {/* Manual Mode Banner */}
      {isManual && (
        <View style={styles.manualBanner}>
          <Text style={styles.manualBannerText}>
            🧪 Manual Input Mode — {weather?.rainfall_mm}mm rainfall
          </Text>
          <TouchableOpacity onPress={() => { setIsManual(false); fetchZones(); }}>
            <Text style={styles.manualBannerBtn}>Auto →</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Disaster Type Buttons */}
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

      {/* Day Toggle */}
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

      {/* Loading Bar */}
      {zonesLoading && (
        <View style={styles.loadingBar}>
          <ActivityIndicator size="small" color="#fff" />
          <Text style={styles.loadingBarText}>
            Fetching {disasterType} zones ({dayType})...
          </Text>
        </View>
      )}

      {/* Error Bar */}
      {error && !zonesLoading && (
        <View style={styles.errorBar}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
          <TouchableOpacity onPress={fetchZones}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Summary Panel */}
      {summary && !zonesLoading && (
        <View style={styles.summaryPanel}>
          <Text style={styles.summaryTitle}>
            {floodActive ? "🌊 Flood Risk" : "⛰️ Landslide Risk"}
            {isManual ? " — Manual" : dayType === "today" ? " — Today" : " — Tomorrow"}
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

      {/* Legend */}
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

const styles = StyleSheet.create({
  container:      { flex: 1, backgroundColor: "#f5f5f5" },
  map:            { flex: 1 },
  centered:       { flex: 1, alignItems: "center", justifyContent: "center" },
  loadingText:    { marginTop: 10, color: "#555", fontSize: 14 },
  placeholderMap: { flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#e0f2fe" },
  title:          { fontSize: 24, fontWeight: "bold", textAlign: "center", color: "#0c4a6e" },
  subtitle:       { fontSize: 16, textAlign: "center", marginTop: 10, color: "#0369a1" },

  manualBanner: {
    position: "absolute", top: 0, left: 0, right: 0,
    backgroundColor: "#7C3AED", flexDirection: "row",
    alignItems: "center", justifyContent: "space-between",
    paddingVertical: 10, paddingHorizontal: 16, zIndex: 20,
  },
  manualBannerText: { color: "#fff", fontSize: 13, fontWeight: "600", flex: 1 },
  manualBannerBtn:  { color: "#E9D5FF", fontSize: 13, fontWeight: "700", marginLeft: 10 },

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
  typeBtnText:            { fontSize: 14, fontWeight: "600", color: "#64748b" },
  typeBtnTextActive:      { color: "#fff" },

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
  dayBtnActive:     { backgroundColor: "#0ea5e9" },
  dayBtnText:       { fontSize: 13, fontWeight: "600", color: "#64748b" },
  dayBtnTextActive: { color: "#fff" },

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
  errorText: { fontSize: 12, color: "#DC2626", flex: 1 },
  retryText: { fontSize: 12, color: "#0ea5e9", fontWeight: "700", marginLeft: 8 },

  summaryPanel: {
    position: "absolute", bottom: 20, left: 16, right: 16,
    backgroundColor: "rgba(255,255,255,0.96)", borderRadius: 16,
    padding: 14, elevation: 6,
    shadowColor: "#000", shadowOpacity: 0.15,
    shadowRadius: 8, shadowOffset: { width: 0, height: 3 },
  },
  summaryTitle:  { fontSize: 14, fontWeight: "700", color: "#0F172A", marginBottom: 10 },
  summaryRow:    { flexDirection: "row", justifyContent: "space-around", marginBottom: 8 },
  summaryItem:   { alignItems: "center", gap: 4 },
  summaryDot:    { width: 12, height: 12, borderRadius: 6 },
  summaryCount:  { fontSize: 20, fontWeight: "800", color: "#0F172A" },
  summaryLabel:  { fontSize: 11, color: "#64748B" },
  weatherText:   { fontSize: 12, color: "#475569", textAlign: "center", marginTop: 4 },
  updatedText:   { fontSize: 10, color: "#94A3B8", textAlign: "center", marginTop: 4 },

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


