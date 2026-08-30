// import React, { useState } from "react";
// import { View, Text, StyleSheet, TextInput, TouchableOpacity, ScrollView, ActivityIndicator, Alert } from "react-native";
// import { getDailyFloodRisk } from "../services/disasterApi";

// const BOUNDS = { latMin: 6.9, latMax: 7.275, lngMin: 79.85, lngMax: 80.35 };

// export default function ManualInputScreen() {
//   const [latitude, setLatitude] = useState("7.1");
//   const [longitude, setLongitude] = useState("80.05");
//   const [dayOffset, setDayOffset] = useState(0);
//   const [loading, setLoading] = useState(false);
//   const [result, setResult] = useState(null);

//   const handleCheck = async () => {
//     const lat = Number(latitude);
//     const lng = Number(longitude);
//     if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
//       Alert.alert("Invalid coordinates", "Enter valid latitude and longitude values.");
//       return;
//     }
//     if (lat < BOUNDS.latMin || lat > BOUNDS.latMax || lng < BOUNDS.lngMin || lng > BOUNDS.lngMax) {
//       Alert.alert("Outside study area", "Latitude: 6.9–7.275, longitude: 79.85–80.35.");
//       return;
//     }
//     setLoading(true);
//     setResult(null);
//     try {
//       setResult(await getDailyFloodRisk(lat, lng, dayOffset));
//     } catch (error) {
//       Alert.alert("Connection failed", "Start FastAPI with --host 0.0.0.0 and keep both devices on the same hotspot.");
//       console.error("Daily flood check failed:", error);
//     } finally {
//       setLoading(false);
//     }
//   };

//   const riskColor = result?.risk_level === "high" ? "#DC2626" : result?.risk_level === "warning" ? "#EA580C" : "#16A34A";

//   return (
//     <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">
//       <View style={styles.header}>
//         <Text style={styles.headerTitle}>📍 Check Flood Risk</Text>
//         <Text style={styles.headerSub}>Enter a Gampaha coordinate. The backend obtains the weather automatically.</Text>
//       </View>
//       <View style={styles.card}>
//         <Text style={styles.cardTitle}>Location</Text>
//         <Text style={styles.label}>Latitude</Text>
//         <TextInput style={styles.input} value={latitude} onChangeText={setLatitude} keyboardType="decimal-pad" placeholder="7.1000" />
//         <Text style={styles.hint}>Supported: 6.9–7.275</Text>
//         <Text style={[styles.label, styles.spacedLabel]}>Longitude</Text>
//         <TextInput style={styles.input} value={longitude} onChangeText={setLongitude} keyboardType="decimal-pad" placeholder="80.0500" />
//         <Text style={styles.hint}>Supported: 79.85–80.35</Text>
//       </View>
//       <View style={styles.dayRow}>
//         {[0, 1].map((offset) => (
//           <TouchableOpacity key={offset} style={[styles.dayButton, dayOffset === offset && styles.dayButtonActive]} onPress={() => setDayOffset(offset)}>
//             <Text style={[styles.dayText, dayOffset === offset && styles.dayTextActive]}>{offset === 0 ? "Today" : "Tomorrow"}</Text>
//           </TouchableOpacity>
//         ))}
//       </View>
//       <TouchableOpacity style={styles.checkButton} onPress={handleCheck} disabled={loading}>
//         {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.checkText}>Check Flood Risk</Text>}
//       </TouchableOpacity>
//       {result && (
//         <View style={[styles.resultCard, { borderColor: riskColor }]}>
//           <Text style={styles.resultTitle}>Result for {result.date}</Text>
//           <Text style={[styles.riskLevel, { color: riskColor }]}>{result.risk_level.toUpperCase()} RISK</Text>
//           <Text style={styles.probability}>Model probability: {(result.flood_probability * 100).toFixed(1)}%</Text>
//           <View style={styles.divider} />
//           <Text style={styles.value}>Target-day rainfall: {result.weather.target_day_rainfall_mm} mm</Text>
//           <Text style={styles.value}>3-day rainfall: {result.weather.rain_3d_mm} mm</Text>
//           <Text style={styles.value}>7-day rainfall: {result.weather.rain_7d_mm} mm</Text>
//           <Text style={styles.value}>Elevation: {result.terrain.elevation_m} m</Text>
//           <Text style={styles.value}>River proximity: {result.terrain.river_proximity_km} km</Text>
//           <Text style={styles.source}>Source: {result.data_source}</Text>
//           <Text style={styles.warning}>Predicted risk is not confirmation of observed flooding. Check official DMC warnings.</Text>
//         </View>
//       )}
//       <View style={{ height: 40 }} />
//     </ScrollView>
//   );
// }

// const styles = StyleSheet.create({
//   container: { flex: 1, backgroundColor: "#F0F9FF" },
//   header: { backgroundColor: "#0EA5E9", padding: 24, paddingTop: 36, borderBottomLeftRadius: 24, borderBottomRightRadius: 24 },
//   headerTitle: { fontSize: 22, fontWeight: "800", color: "#fff", marginBottom: 6 },
//   headerSub: { fontSize: 13, color: "rgba(255,255,255,0.9)", lineHeight: 19 },
//   card: { backgroundColor: "#fff", margin: 16, padding: 16, borderRadius: 16, elevation: 2 },
//   cardTitle: { fontSize: 17, fontWeight: "700", color: "#0F172A", marginBottom: 14 },
//   label: { fontSize: 13, fontWeight: "600", color: "#334155", marginBottom: 6 },
//   spacedLabel: { marginTop: 16 },
//   input: { borderWidth: 1.5, borderColor: "#CBD5E1", borderRadius: 10, padding: 12, fontSize: 16, color: "#0F172A" },
//   hint: { color: "#64748B", fontSize: 11, marginTop: 4 },
//   dayRow: { flexDirection: "row", gap: 10, marginHorizontal: 16, marginBottom: 14 },
//   dayButton: { flex: 1, alignItems: "center", padding: 12, borderRadius: 10, backgroundColor: "#fff" },
//   dayButtonActive: { backgroundColor: "#0284C7" },
//   dayText: { color: "#64748B", fontWeight: "700" },
//   dayTextActive: { color: "#fff" },
//   checkButton: { marginHorizontal: 16, backgroundColor: "#0EA5E9", padding: 16, borderRadius: 14, alignItems: "center" },
//   checkText: { color: "#fff", fontSize: 16, fontWeight: "700" },
//   resultCard: { margin: 16, padding: 16, backgroundColor: "#fff", borderRadius: 16, borderWidth: 2 },
//   resultTitle: { color: "#475569", fontSize: 13, textAlign: "center" },
//   riskLevel: { fontSize: 24, fontWeight: "900", textAlign: "center", marginTop: 5 },
//   probability: { color: "#334155", textAlign: "center", marginTop: 4 },
//   divider: { height: 1, backgroundColor: "#E2E8F0", marginVertical: 14 },
//   value: { color: "#334155", fontSize: 13, marginBottom: 7 },
//   source: { color: "#64748B", fontSize: 11, marginTop: 8 },
//   warning: { color: "#92400E", backgroundColor: "#FFFBEB", padding: 10, borderRadius: 8, fontSize: 11, lineHeight: 16, marginTop: 12 },
// });
import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  Alert,
} from "react-native";

import { getDailyFloodRisk } from "../services/disasterApi";

const BOUNDS = {
  latMin: 6.9,
  latMax: 7.275,
  lngMin: 79.85,
  lngMax: 80.35,
};

const GAMPAHA_LOCATIONS = [
  {
    name: "Gampaha Town",
    latitude: 7.0873,
    longitude: 79.999,
  },
  {
    name: "Mirigama",
    latitude: 7.2414,
    longitude: 80.1325,
  },
  {
    name: "Minuwangoda",
    latitude: 7.1663,
    longitude: 79.9533,
  },
  {
    name: "Divulapitiya",
    latitude: 7.224,
    longitude: 80.0193,
  },
  {
    name: "Veyangoda",
    latitude: 7.1568,
    longitude: 80.0954,
  },
  {
    name: "Nittambuwa",
    latitude: 7.1443,
    longitude: 80.096,
  },
  {
    name: "Kirindiwela",
    latitude: 7.0442,
    longitude: 80.1266,
  },
  {
    name: "Kadawatha",
    latitude: 7.0013,
    longitude: 79.9508,
  },
  {
    name: "Ragama",
    latitude: 7.025,
    longitude: 79.9178,
  },
  {
    name: "Ja-Ela",
    latitude: 7.0744,
    longitude: 79.8919,
  },
  {
    name: "Wattala",
    latitude: 6.99,
    longitude: 79.892,
  },
  {
    name: "Kelaniya",
    latitude: 6.9553,
    longitude: 79.922,
  },
  {
    name: "Biyagama",
    latitude: 6.9408,
    longitude: 79.9842,
  },
  {
    name: "Dompe",
    latitude: 6.9498,
    longitude: 80.0555,
  },
];

export default function ManualInputScreen() {
  const [locationSearch, setLocationSearch] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [latitude, setLatitude] = useState("7.1");
  const [longitude, setLongitude] = useState("80.05");

  const [dayOffset, setDayOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const matchingLocations = locationSearch.trim()
    ? GAMPAHA_LOCATIONS.filter((location) =>
        location.name
          .toLowerCase()
          .includes(locationSearch.trim().toLowerCase()),
      ).slice(0, 6)
    : [];

  const selectLocation = (location) => {
    setLocationSearch(location.name);
    setLatitude(String(location.latitude));
    setLongitude(String(location.longitude));
    setShowSuggestions(false);
    setResult(null);
  };

  const handleCheck = async () => {
    const lat = Number(latitude);
    const lng = Number(longitude);

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      Alert.alert(
        "Invalid coordinates",
        "Enter valid latitude and longitude values.",
      );
      return;
    }

    const isOutsideBoundary =
      lat < BOUNDS.latMin ||
      lat > BOUNDS.latMax ||
      lng < BOUNDS.lngMin ||
      lng > BOUNDS.lngMax;

    if (isOutsideBoundary) {
      Alert.alert(
        "Outside study area",
        "Latitude: 6.9–7.275, longitude: 79.85–80.35.",
      );
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const prediction = await getDailyFloodRisk(
        lat,
        lng,
        dayOffset,
      );

      setResult(prediction);
    } catch (error) {
      Alert.alert(
        "Connection failed",
        "Start FastAPI and keep the USB cable connected.",
      );

      console.error("Daily flood check failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const riskColor =
    result?.risk_level === "high"
      ? "#DC2626"
      : result?.risk_level === "warning"
        ? "#EA580C"
        : "#16A34A";

  return (
    <ScrollView
      style={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>
          📍 Check Flood Risk
        </Text>

        <Text style={styles.headerSub}>
          Search for a Gampaha location or manually enter
          coordinates. Weather data is obtained automatically.
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>
          Search Location
        </Text>

        <Text style={styles.label}>
          Town or area
        </Text>

        <TextInput
          style={styles.input}
          value={locationSearch}
          onChangeText={(text) => {
            setLocationSearch(text);
            setShowSuggestions(true);
          }}
          onFocus={() => setShowSuggestions(true)}
          placeholder="e.g. Gampaha Town or Mirigama"
          placeholderTextColor="#94A3B8"
          autoCapitalize="words"
        />

        {showSuggestions &&
          locationSearch.trim().length > 0 && (
            <View style={styles.suggestions}>
              {matchingLocations.length > 0 ? (
                matchingLocations.map((location) => (
                  <TouchableOpacity
                    key={location.name}
                    style={styles.suggestionItem}
                    onPress={() =>
                      selectLocation(location)
                    }
                  >
                    <Text style={styles.suggestionName}>
                      📍 {location.name}
                    </Text>

                    <Text style={styles.suggestionCoords}>
                      {location.latitude},{" "}
                      {location.longitude}
                    </Text>
                  </TouchableOpacity>
                ))
              ) : (
                <Text style={styles.noLocation}>
                  Location is not in the supported town
                  list. Enter coordinates below.
                </Text>
              )}
            </View>
          )}

        <View style={styles.coordinateDivider}>
          <View style={styles.dividerLine} />

          <Text style={styles.dividerLabel}>
            or enter coordinates
          </Text>

          <View style={styles.dividerLine} />
        </View>

        <Text style={styles.label}>
          Latitude
        </Text>

        <TextInput
          style={styles.input}
          value={latitude}
          onChangeText={(text) => {
            setLatitude(text);
            setResult(null);
          }}
          keyboardType="decimal-pad"
          placeholder="7.1000"
          placeholderTextColor="#94A3B8"
        />

        <Text style={styles.hint}>
          Supported: 6.9–7.275
        </Text>

        <Text style={[styles.label, styles.spacedLabel]}>
          Longitude
        </Text>

        <TextInput
          style={styles.input}
          value={longitude}
          onChangeText={(text) => {
            setLongitude(text);
            setResult(null);
          }}
          keyboardType="decimal-pad"
          placeholder="80.0500"
          placeholderTextColor="#94A3B8"
        />

        <Text style={styles.hint}>
          Supported: 79.85–80.35
        </Text>
      </View>

      <View style={styles.dayRow}>
        <TouchableOpacity
          style={[
            styles.dayButton,
            dayOffset === 0 &&
              styles.dayButtonActive,
          ]}
          onPress={() => {
            setDayOffset(0);
            setResult(null);
          }}
        >
          <Text
            style={[
              styles.dayText,
              dayOffset === 0 &&
                styles.dayTextActive,
            ]}
          >
            Today
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.dayButton,
            dayOffset === 1 &&
              styles.dayButtonActive,
          ]}
          onPress={() => {
            setDayOffset(1);
            setResult(null);
          }}
        >
          <Text
            style={[
              styles.dayText,
              dayOffset === 1 &&
                styles.dayTextActive,
            ]}
          >
            Tomorrow
          </Text>
        </TouchableOpacity>
      </View>

      <TouchableOpacity
        style={[
          styles.checkButton,
          loading && styles.checkButtonDisabled,
        ]}
        onPress={handleCheck}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.checkText}>
            Check Flood Risk
          </Text>
        )}
      </TouchableOpacity>

      {result && (
        <View
          style={[
            styles.resultCard,
            { borderColor: riskColor },
          ]}
        >
          <Text style={styles.resultTitle}>
            {locationSearch || "Selected location"}
          </Text>

          <Text style={styles.resultDate}>
            Result for {result.date}
          </Text>

          <Text
            style={[
              styles.riskLevel,
              { color: riskColor },
            ]}
          >
            {result.risk_level.toUpperCase()} RISK
          </Text>

          <Text style={styles.probability}>
            Model probability:{" "}
            {(result.flood_probability * 100).toFixed(1)}%
          </Text>

          <View style={styles.resultDivider} />

          <Text style={styles.value}>
            Target-day rainfall:{" "}
            {result.weather.target_day_rainfall_mm} mm
          </Text>

          <Text style={styles.value}>
            3-day rainfall:{" "}
            {result.weather.rain_3d_mm} mm
          </Text>

          <Text style={styles.value}>
            7-day rainfall:{" "}
            {result.weather.rain_7d_mm} mm
          </Text>

          <Text style={styles.value}>
            Elevation:{" "}
            {result.terrain.elevation_m} m
          </Text>

          <Text style={styles.value}>
            River proximity:{" "}
            {result.terrain.river_proximity_km} km
          </Text>

          <Text style={styles.source}>
            Source: {result.data_source}
          </Text>

          <Text style={styles.warning}>
            This is predicted risk, not confirmation
            of observed flooding. Check official DMC
            warnings.
          </Text>
        </View>
      )}

      <View style={styles.bottomSpace} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F0F9FF",
  },

  header: {
    backgroundColor: "#0EA5E9",
    padding: 24,
    paddingTop: 36,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },

  headerTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#FFFFFF",
    marginBottom: 6,
  },

  headerSub: {
    fontSize: 13,
    color: "rgba(255,255,255,0.9)",
    lineHeight: 19,
  },

  card: {
    backgroundColor: "#FFFFFF",
    margin: 16,
    padding: 16,
    borderRadius: 16,
    elevation: 2,
  },

  cardTitle: {
    fontSize: 17,
    fontWeight: "700",
    color: "#0F172A",
    marginBottom: 14,
  },

  label: {
    fontSize: 13,
    fontWeight: "600",
    color: "#334155",
    marginBottom: 6,
  },

  spacedLabel: {
    marginTop: 16,
  },

  input: {
    borderWidth: 1.5,
    borderColor: "#CBD5E1",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: "#0F172A",
    backgroundColor: "#FFFFFF",
  },

  hint: {
    color: "#64748B",
    fontSize: 11,
    marginTop: 4,
  },

  suggestions: {
    borderWidth: 1,
    borderColor: "#BAE6FD",
    borderRadius: 10,
    marginTop: 6,
    overflow: "hidden",
  },

  suggestionItem: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    backgroundColor: "#F0F9FF",
    borderBottomWidth: 1,
    borderBottomColor: "#E0F2FE",
  },

  suggestionName: {
    color: "#0C4A6E",
    fontSize: 14,
    fontWeight: "700",
  },

  suggestionCoords: {
    color: "#64748B",
    fontSize: 11,
    marginTop: 2,
    marginLeft: 21,
  },

  noLocation: {
    color: "#92400E",
    fontSize: 12,
    lineHeight: 17,
    padding: 12,
    backgroundColor: "#FFFBEB",
  },

  coordinateDivider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 18,
  },

  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: "#E2E8F0",
  },

  dividerLabel: {
    color: "#94A3B8",
    fontSize: 11,
    marginHorizontal: 8,
  },

  dayRow: {
    flexDirection: "row",
    gap: 10,
    marginHorizontal: 16,
    marginBottom: 14,
  },

  dayButton: {
    flex: 1,
    alignItems: "center",
    padding: 12,
    borderRadius: 10,
    backgroundColor: "#FFFFFF",
  },

  dayButtonActive: {
    backgroundColor: "#0284C7",
  },

  dayText: {
    color: "#64748B",
    fontWeight: "700",
  },

  dayTextActive: {
    color: "#FFFFFF",
  },

  checkButton: {
    marginHorizontal: 16,
    backgroundColor: "#0EA5E9",
    padding: 16,
    borderRadius: 14,
    alignItems: "center",
  },

  checkButtonDisabled: {
    opacity: 0.7,
  },

  checkText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },

  resultCard: {
    margin: 16,
    padding: 16,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    borderWidth: 2,
  },

  resultTitle: {
    color: "#0F172A",
    fontSize: 17,
    fontWeight: "700",
    textAlign: "center",
  },

  resultDate: {
    color: "#475569",
    fontSize: 12,
    textAlign: "center",
    marginTop: 3,
  },

  riskLevel: {
    fontSize: 24,
    fontWeight: "900",
    textAlign: "center",
    marginTop: 8,
  },

  probability: {
    color: "#334155",
    textAlign: "center",
    marginTop: 4,
  },

  resultDivider: {
    height: 1,
    backgroundColor: "#E2E8F0",
    marginVertical: 14,
  },

  value: {
    color: "#334155",
    fontSize: 13,
    marginBottom: 7,
  },

  source: {
    color: "#64748B",
    fontSize: 11,
    marginTop: 8,
  },

  warning: {
    color: "#92400E",
    backgroundColor: "#FFFBEB",
    padding: 10,
    borderRadius: 8,
    fontSize: 11,
    lineHeight: 16,
    marginTop: 12,
  },

  bottomSpace: {
    height: 40,
  },
});
