// /**
//  * ManualInputScreen.js
//  * Suraksha Lanka — Manual Weather Input
//  * Project: R26-IT-151 | Student: IT22294470
//  *
//  * User manually enters weather values →
//  * Backend predict → Map zones display
//  */

// import React, { useState } from "react";
// import {
//   View, Text, StyleSheet, TextInput,
//   TouchableOpacity, ScrollView, ActivityIndicator, Alert
// } from "react-native";
// import { getFloodZonesManual, getLandslideZonesManual } from "../services/disasterApi";

// export default function ManualInputScreen({ navigation }) {
//   const [rainfall,    setRainfall]    = useState("");
//   const [humidity,    setHumidity]    = useState("");
//   const [temperature, setTemperature] = useState("");
//   const [wind,        setWind]        = useState("");
//   const [disasterType, setDisasterType] = useState("flood");
//   const [loading,     setLoading]     = useState(false);

//   const handlePredict = async () => {
//     // Validate inputs
//     if (!rainfall || !humidity || !temperature || !wind) {
//       Alert.alert("⚠️ Error", "සියලු fields fill කරන්න!");
//       return;
//     }

//     const input = {
//       rainfall_mm:    parseFloat(rainfall),
//       humidity_pct:   parseFloat(humidity),
//       temperature_c:  parseFloat(temperature),
//       wind_speed_kmh: parseFloat(wind),
//     };

//     // Validate ranges
//     if (input.rainfall_mm < 0 || input.rainfall_mm > 500) {
//       Alert.alert("⚠️ Error", "Rainfall: 0-500mm ඇතුළේ දාන්න");
//       return;
//     }
//     if (input.humidity_pct < 0 || input.humidity_pct > 100) {
//       Alert.alert("⚠️ Error", "Humidity: 0-100% ඇතුළේ දාන්න");
//       return;
//     }

//     setLoading(true);
//     try {
//       const response = disasterType === "flood"
//         ? await getFloodZonesManual(input)
//         : await getLandslideZonesManual(input);

//       // Navigate to Map screen with results
//       navigation.navigate("Map", {
//         manualZones:   response.zones,
//         manualSummary: response.summary,
//         manualWeather: input,
//         disasterType,
//         dayLabel:      "manual",
//       });
//     } catch (err) {
//       Alert.alert("❌ Error", "Backend connect වෙන්න බෑ. Backend running ද check කරන්න.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   const fillExample = (type) => {
//     if (type === "flood") {
//       setRainfall("120");
//       setHumidity("95");
//       setTemperature("26");
//       setWind("25");
//     } else if (type === "dry") {
//       setRainfall("2");
//       setHumidity("60");
//       setTemperature("31");
//       setWind("8");
//     }
//   };

//   return (
//     <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">

//       {/* Header */}
//       <View style={styles.header}>
//         <Text style={styles.headerTitle}>🌦️ Manual Weather Input</Text>
//         <Text style={styles.headerSub}>
//           Weather values manually enter කරලා risk zones predict කරන්න
//         </Text>
//       </View>

//       {/* Disaster Type Toggle */}
//       <View style={styles.typeRow}>
//         <TouchableOpacity
//           style={[styles.typeBtn, disasterType === "flood" && styles.typeBtnFloodActive]}
//           onPress={() => setDisasterType("flood")}
//         >
//           <Text style={[styles.typeBtnText, disasterType === "flood" && styles.typeBtnTextActive]}>
//             🌊 Flood
//           </Text>
//         </TouchableOpacity>
//         <TouchableOpacity
//           style={[styles.typeBtn, disasterType === "landslide" && styles.typeBtnLandslideActive]}
//           onPress={() => setDisasterType("landslide")}
//         >
//           <Text style={[styles.typeBtnText, disasterType === "landslide" && styles.typeBtnTextActive]}>
//             ⛰️ Landslide
//           </Text>
//         </TouchableOpacity>
//       </View>

//       {/* Input Fields */}
//       <View style={styles.card}>
//         <Text style={styles.cardTitle}>Weather Values</Text>

//         {/* Rainfall */}
//         <View style={styles.inputGroup}>
//           <Text style={styles.label}>🌧️ Rainfall (mm)</Text>
//           <TextInput
//             style={styles.input}
//             value={rainfall}
//             onChangeText={setRainfall}
//             keyboardType="numeric"
//             placeholder="e.g. 75"
//             placeholderTextColor="#94A3B8"
//           />
//           <Text style={styles.hint}>Range: 0 - 500mm</Text>
//         </View>

//         {/* Humidity */}
//         <View style={styles.inputGroup}>
//           <Text style={styles.label}>💧 Humidity (%)</Text>
//           <TextInput
//             style={styles.input}
//             value={humidity}
//             onChangeText={setHumidity}
//             keyboardType="numeric"
//             placeholder="e.g. 90"
//             placeholderTextColor="#94A3B8"
//           />
//           <Text style={styles.hint}>Range: 0 - 100%</Text>
//         </View>

//         {/* Temperature */}
//         <View style={styles.inputGroup}>
//           <Text style={styles.label}>🌡️ Temperature (°C)</Text>
//           <TextInput
//             style={styles.input}
//             value={temperature}
//             onChangeText={setTemperature}
//             keyboardType="numeric"
//             placeholder="e.g. 27"
//             placeholderTextColor="#94A3B8"
//           />
//           <Text style={styles.hint}>Range: 20 - 35°C</Text>
//         </View>

//         {/* Wind Speed */}
//         <View style={styles.inputGroup}>
//           <Text style={styles.label}>💨 Wind Speed (km/h)</Text>
//           <TextInput
//             style={styles.input}
//             value={wind}
//             onChangeText={setWind}
//             keyboardType="numeric"
//             placeholder="e.g. 15"
//             placeholderTextColor="#94A3B8"
//           />
//           <Text style={styles.hint}>Range: 0 - 100 km/h</Text>
//         </View>
//       </View>

//       {/* Quick Fill Buttons */}
//       <View style={styles.card}>
//         <Text style={styles.cardTitle}>Quick Fill Examples</Text>
//         <View style={styles.exampleRow}>
//           <TouchableOpacity
//             style={[styles.exampleBtn, { backgroundColor: "#FEE2E2" }]}
//             onPress={() => fillExample("flood")}
//           >
//             <Text style={styles.exampleBtnText}>🌊 Heavy Rain Scenario</Text>
//             <Text style={styles.exampleBtnSub}>120mm | 95% | 26°C | 25km/h</Text>
//           </TouchableOpacity>

//           <TouchableOpacity
//             style={[styles.exampleBtn, { backgroundColor: "#DCFCE7" }]}
//             onPress={() => fillExample("dry")}
//           >
//             <Text style={styles.exampleBtnText}>☀️ Dry Day Scenario</Text>
//             <Text style={styles.exampleBtnSub}>2mm | 60% | 31°C | 8km/h</Text>
//           </TouchableOpacity>
//         </View>
//       </View>

//       {/* Predict Button */}
//       <TouchableOpacity
//         style={[styles.predictBtn, loading && styles.predictBtnDisabled]}
//         onPress={handlePredict}
//         disabled={loading}
//       >
//         {loading ? (
//           <ActivityIndicator color="#fff" size="small" />
//         ) : (
//           <Text style={styles.predictBtnText}>
//             🔍 Predict {disasterType === "flood" ? "Flood" : "Landslide"} Zones
//           </Text>
//         )}
//       </TouchableOpacity>

//       {loading && (
//         <Text style={styles.loadingText}>
//           ⏳ Predicting zones... (~10-30 seconds)
//         </Text>
//       )}

//       <View style={{ height: 40 }} />
//     </ScrollView>
//   );
// }

// const styles = StyleSheet.create({
//   container:       { flex: 1, backgroundColor: "#F0F9FF" },

//   header: {
//     backgroundColor: "#0EA5E9",
//     padding: 24, paddingTop: 40,
//     borderBottomLeftRadius: 24, borderBottomRightRadius: 24,
//   },
//   headerTitle:     { fontSize: 22, fontWeight: "800", color: "#fff", marginBottom: 6 },
//   headerSub:       { fontSize: 13, color: "rgba(255,255,255,0.85)", lineHeight: 18 },

//   typeRow: {
//     flexDirection: "row", margin: 16, gap: 10,
//   },
//   typeBtn: {
//     flex: 1, paddingVertical: 12, borderRadius: 12,
//     backgroundColor: "#fff", alignItems: "center",
//     elevation: 2, shadowColor: "#000", shadowOpacity: 0.08,
//     shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
//   },
//   typeBtnFloodActive:     { backgroundColor: "#3B82F6" },
//   typeBtnLandslideActive: { backgroundColor: "#EF4444" },
//   typeBtnText:            { fontSize: 14, fontWeight: "600", color: "#64748B" },
//   typeBtnTextActive:      { color: "#fff" },

//   card: {
//     backgroundColor: "#fff", marginHorizontal: 16,
//     marginBottom: 12, borderRadius: 16, padding: 16,
//     elevation: 2, shadowColor: "#000", shadowOpacity: 0.06,
//     shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
//   },
//   cardTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A", marginBottom: 14 },

//   inputGroup:  { marginBottom: 14 },
//   label:       { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 6 },
//   input: {
//     borderWidth: 1.5, borderColor: "#E2E8F0", borderRadius: 10,
//     paddingHorizontal: 14, paddingVertical: 12,
//     fontSize: 16, color: "#0F172A", backgroundColor: "#F8FAFC",
//   },
//   hint: { fontSize: 11, color: "#94A3B8", marginTop: 4 },

//   exampleRow:    { gap: 10 },
//   exampleBtn: {
//     padding: 12, borderRadius: 10, marginBottom: 4,
//   },
//   exampleBtnText: { fontSize: 13, fontWeight: "600", color: "#0F172A", marginBottom: 2 },
//   exampleBtnSub:  { fontSize: 11, color: "#64748B" },

//   predictBtn: {
//     marginHorizontal: 16, marginTop: 8,
//     backgroundColor: "#0EA5E9", paddingVertical: 16,
//     borderRadius: 14, alignItems: "center",
//     elevation: 4, shadowColor: "#0EA5E9",
//     shadowOpacity: 0.3, shadowRadius: 8,
//     shadowOffset: { width: 0, height: 4 },
//   },
//   predictBtnDisabled: { backgroundColor: "#93C5FD" },
//   predictBtnText:     { fontSize: 16, fontWeight: "700", color: "#fff" },
//   loadingText: {
//     textAlign: "center", color: "#64748B",
//     fontSize: 13, marginTop: 10,
//   },
// });


/**
 * ManualInputScreen.js
 * Suraksha Lanka — Manual Weather Input
 * Project: R26-IT-151 | Student: IT22294470
 *
 * User manually enters weather values →
 * Backend predict → Map zones display
 */

import React, { useState } from "react";
import {
  View, Text, StyleSheet, TextInput,
  TouchableOpacity, ScrollView, ActivityIndicator, Alert
} from "react-native";
import { getFloodZonesManual, getLandslideZonesManual } from "../services/disasterApi";

export default function ManualInputScreen({ navigation }) {
  const [rainfall,    setRainfall]    = useState("");
  const [humidity,    setHumidity]    = useState("");
  const [temperature, setTemperature] = useState("");
  const [wind,        setWind]        = useState("");
  const [disasterType, setDisasterType] = useState("flood");
  const [loading,     setLoading]     = useState(false);

  const handlePredict = async () => {
    // Validate inputs
    if (!rainfall || !humidity || !temperature || !wind) {
      Alert.alert("⚠️ Error", "සියලු fields fill කරන්න!");
      return;
    }

    const input = {
      rainfall_mm:    parseFloat(rainfall),
      humidity_pct:   parseFloat(humidity),
      temperature_c:  parseFloat(temperature),
      wind_speed_kmh: parseFloat(wind),
    };

    // Validate ranges
    if (input.rainfall_mm < 0 || input.rainfall_mm > 500) {
      Alert.alert("⚠️ Error", "Rainfall: 0-500mm ඇතුළේ දාන්න");
      return;
    }
    if (input.humidity_pct < 0 || input.humidity_pct > 100) {
      Alert.alert("⚠️ Error", "Humidity: 0-100% ඇතුළේ දාන්න");
      return;
    }

    setLoading(true);
    try {
      const response = disasterType === "flood"
        ? await getFloodZonesManual(input)
        : await getLandslideZonesManual(input);

      // Navigate to Map screen with results
      navigation.navigate("Map", {
        manualZones:   response.zones,
        manualSummary: response.summary,
        manualWeather: input,
        disasterType,
        dayLabel:      "manual",
      });
    } catch (err) {
      Alert.alert("❌ Error", "Backend connect වෙන්න බෑ. Backend running ද check කරන්න.");
    } finally {
      setLoading(false);
    }
  };

  const fillExample = (type) => {
    if (type === "flood") {
      setRainfall("120");
      setHumidity("95");
      setTemperature("26");
      setWind("25");
    } else if (type === "dry") {
      setRainfall("2");
      setHumidity("60");
      setTemperature("31");
      setWind("8");
    }
  };

  return (
    <ScrollView style={styles.container} keyboardShouldPersistTaps="handled">

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🌦️ Manual Weather Input</Text>
        <Text style={styles.headerSub}>
          Weather values manually enter කරලා risk zones predict කරන්න
        </Text>
      </View>

      {/* Disaster Type Toggle */}
      <View style={styles.typeRow}>
        <TouchableOpacity
          style={[styles.typeBtn, disasterType === "flood" && styles.typeBtnFloodActive]}
          onPress={() => setDisasterType("flood")}
        >
          <Text style={[styles.typeBtnText, disasterType === "flood" && styles.typeBtnTextActive]}>
            🌊 Flood
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.typeBtn, disasterType === "landslide" && styles.typeBtnLandslideActive]}
          onPress={() => setDisasterType("landslide")}
        >
          <Text style={[styles.typeBtnText, disasterType === "landslide" && styles.typeBtnTextActive]}>
            ⛰️ Landslide
          </Text>
        </TouchableOpacity>
      </View>

      {/* Input Fields */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Weather Values</Text>

        {/* Rainfall */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>🌧️ Rainfall (mm)</Text>
          <TextInput
            style={styles.input}
            value={rainfall}
            onChangeText={setRainfall}
            keyboardType="numeric"
            placeholder="e.g. 75"
            placeholderTextColor="#94A3B8"
          />
          <Text style={styles.hint}>Range: 0 - 500mm</Text>
        </View>

        {/* Humidity */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>💧 Humidity (%)</Text>
          <TextInput
            style={styles.input}
            value={humidity}
            onChangeText={setHumidity}
            keyboardType="numeric"
            placeholder="e.g. 90"
            placeholderTextColor="#94A3B8"
          />
          <Text style={styles.hint}>Range: 0 - 100%</Text>
        </View>

        {/* Temperature */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>🌡️ Temperature (°C)</Text>
          <TextInput
            style={styles.input}
            value={temperature}
            onChangeText={setTemperature}
            keyboardType="numeric"
            placeholder="e.g. 27"
            placeholderTextColor="#94A3B8"
          />
          <Text style={styles.hint}>Range: 20 - 35°C</Text>
        </View>

        {/* Wind Speed */}
        <View style={styles.inputGroup}>
          <Text style={styles.label}>💨 Wind Speed (km/h)</Text>
          <TextInput
            style={styles.input}
            value={wind}
            onChangeText={setWind}
            keyboardType="numeric"
            placeholder="e.g. 15"
            placeholderTextColor="#94A3B8"
          />
          <Text style={styles.hint}>Range: 0 - 100 km/h</Text>
        </View>
      </View>

      {/* Quick Fill Buttons */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Quick Fill Examples</Text>
        <View style={styles.exampleRow}>
          <TouchableOpacity
            style={[styles.exampleBtn, { backgroundColor: "#FEE2E2" }]}
            onPress={() => fillExample("flood")}
          >
            <Text style={styles.exampleBtnText}>🌊 Heavy Rain Scenario</Text>
            <Text style={styles.exampleBtnSub}>120mm | 95% | 26°C | 25km/h</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.exampleBtn, { backgroundColor: "#DCFCE7" }]}
            onPress={() => fillExample("dry")}
          >
            <Text style={styles.exampleBtnText}>☀️ Dry Day Scenario</Text>
            <Text style={styles.exampleBtnSub}>2mm | 60% | 31°C | 8km/h</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Predict Button */}
      <TouchableOpacity
        style={[styles.predictBtn, loading && styles.predictBtnDisabled]}
        onPress={handlePredict}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" size="small" />
        ) : (
          <Text style={styles.predictBtnText}>
            🔍 Predict {disasterType === "flood" ? "Flood" : "Landslide"} Zones
          </Text>
        )}
      </TouchableOpacity>

      {loading && (
        <Text style={styles.loadingText}>
          ⏳ Predicting zones... (~10-30 seconds)
        </Text>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: "#F0F9FF" },

  header: {
    backgroundColor: "#0EA5E9",
    padding: 24, paddingTop: 40,
    borderBottomLeftRadius: 24, borderBottomRightRadius: 24,
  },
  headerTitle:     { fontSize: 22, fontWeight: "800", color: "#fff", marginBottom: 6 },
  headerSub:       { fontSize: 13, color: "rgba(255,255,255,0.85)", lineHeight: 18 },

  typeRow: {
    flexDirection: "row", margin: 16, gap: 10,
  },
  typeBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 12,
    backgroundColor: "#fff", alignItems: "center",
    elevation: 2, shadowColor: "#000", shadowOpacity: 0.08,
    shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
  },
  typeBtnFloodActive:     { backgroundColor: "#3B82F6" },
  typeBtnLandslideActive: { backgroundColor: "#EF4444" },
  typeBtnText:            { fontSize: 14, fontWeight: "600", color: "#64748B" },
  typeBtnTextActive:      { color: "#fff" },

  card: {
    backgroundColor: "#fff", marginHorizontal: 16,
    marginBottom: 12, borderRadius: 16, padding: 16,
    elevation: 2, shadowColor: "#000", shadowOpacity: 0.06,
    shadowRadius: 4, shadowOffset: { width: 0, height: 2 },
  },
  cardTitle: { fontSize: 16, fontWeight: "700", color: "#0F172A", marginBottom: 14 },

  inputGroup:  { marginBottom: 14 },
  label:       { fontSize: 13, fontWeight: "600", color: "#374151", marginBottom: 6 },
  input: {
    borderWidth: 1.5, borderColor: "#E2E8F0", borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 16, color: "#0F172A", backgroundColor: "#F8FAFC",
  },
  hint: { fontSize: 11, color: "#94A3B8", marginTop: 4 },

  exampleRow:    { gap: 10 },
  exampleBtn: {
    padding: 12, borderRadius: 10, marginBottom: 4,
  },
  exampleBtnText: { fontSize: 13, fontWeight: "600", color: "#0F172A", marginBottom: 2 },
  exampleBtnSub:  { fontSize: 11, color: "#64748B" },

  predictBtn: {
    marginHorizontal: 16, marginTop: 8,
    backgroundColor: "#0EA5E9", paddingVertical: 16,
    borderRadius: 14, alignItems: "center",
    elevation: 4, shadowColor: "#0EA5E9",
    shadowOpacity: 0.3, shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  predictBtnDisabled: { backgroundColor: "#93C5FD" },
  predictBtnText:     { fontSize: 16, fontWeight: "700", color: "#fff" },
  loadingText: {
    textAlign: "center", color: "#64748B",
    fontSize: 13, marginTop: 10,
  },
});

