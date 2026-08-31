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

import { getFloodZonesManual } from "../services/disasterApi";

export default function FloodScenarioScreen({ navigation }) {
  const [rainfall, setRainfall] = useState("150");
  const [humidity, setHumidity] = useState("95");
  const [temperature, setTemperature] = useState("26");
  const [wind, setWind] = useState("18");
  const [loading, setLoading] = useState(false);

  const fillScenario = (type) => {
    if (type === "heavy") {
      setRainfall("200");
      setHumidity("97");
      setTemperature("25");
      setWind("20");
      return;
    }

    if (type === "moderate") {
      setRainfall("90");
      setHumidity("88");
      setTemperature("27");
      setWind("14");
      return;
    }

    setRainfall("5");
    setHumidity("65");
    setTemperature("30");
    setWind("8");
  };

  const runSimulation = async () => {
    const input = {
      rainfall_mm: Number(rainfall),
      humidity_pct: Number(humidity),
      temperature_c: Number(temperature),
      wind_speed_kmh: Number(wind),
    };

    if (
      Object.values(input).some(
        (value) => !Number.isFinite(value),
      )
    ) {
      Alert.alert(
        "Invalid input",
        "Enter a number in every field.",
      );
      return;
    }

    if (
      input.rainfall_mm < 0 ||
      input.rainfall_mm > 2000
    ) {
      Alert.alert(
        "Invalid rainfall",
        "Rainfall must be between 0 and 2000 mm.",
      );
      return;
    }

    if (
      input.humidity_pct < 0 ||
      input.humidity_pct > 100
    ) {
      Alert.alert(
        "Invalid humidity",
        "Humidity must be between 0 and 100%.",
      );
      return;
    }

    if (
      input.temperature_c < -20 ||
      input.temperature_c > 60
    ) {
      Alert.alert(
        "Invalid temperature",
        "Temperature must be between -20 and 60°C.",
      );
      return;
    }

    if (
      input.wind_speed_kmh < 0 ||
      input.wind_speed_kmh > 300
    ) {
      Alert.alert(
        "Invalid wind speed",
        "Wind speed must be between 0 and 300 km/h.",
      );
      return;
    }

    setLoading(true);

    try {
      const response = await getFloodZonesManual(input);

      navigation.navigate("Map", {
        manualZones: response.zones,
        manualSummary: response.summary,
        manualWeather: input,
        disasterType: "flood",
        simulation: true,
      });
    } catch (error) {
      console.error("Flood simulation failed:", error);

      Alert.alert(
        "Simulation failed",
        "Check that the FastAPI backend is running.",
      );
    } finally {
      setLoading(false);
    }
  };

  const InputField = ({
    label,
    value,
    setValue,
    hint,
  }) => (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>

      <TextInput
        style={styles.input}
        value={value}
        onChangeText={setValue}
        keyboardType="decimal-pad"
        placeholderTextColor="#94A3B8"
      />

      <Text style={styles.hint}>{hint}</Text>
    </View>
  );

  return (
    <ScrollView
      style={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.header}>
        <Text style={styles.title}>
          🧪 Flood Scenario Simulation
        </Text>

        <Text style={styles.subtitle}>
          Enter hypothetical weather values to demonstrate
          how model risk zones change.
        </Text>
      </View>

      <View style={styles.notice}>
        <Text style={styles.noticeTitle}>
          ⚠️ Demonstration mode
        </Text>

        <Text style={styles.noticeText}>
          These are manually entered scenario values, not
          current observations. The output is predicted risk,
          not confirmed flooding.
        </Text>
      </View>

      <View style={styles.quickCard}>
        <Text style={styles.cardTitle}>
          Quick scenarios
        </Text>

        <View style={styles.quickRow}>
          <TouchableOpacity
            style={[styles.quickButton, styles.dry]}
            onPress={() => fillScenario("dry")}
          >
            <Text style={styles.quickText}>
              ☀️ Dry
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.quickButton, styles.moderate]}
            onPress={() => fillScenario("moderate")}
          >
            <Text style={styles.quickText}>
              🌧️ Moderate
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.quickButton, styles.heavy]}
            onPress={() => fillScenario("heavy")}
          >
            <Text
              style={[
                styles.quickText,
                { color: "#FFFFFF" },
              ]}
            >
              ⛈️ Heavy
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>
          Manual weather values
        </Text>

        <InputField
          label="🌧️ Rainfall (mm)"
          value={rainfall}
          setValue={setRainfall}
          hint="Scenario rainfall amount"
        />

        <InputField
          label="💧 Humidity (%)"
          value={humidity}
          setValue={setHumidity}
          hint="Range: 0–100%"
        />

        <InputField
          label="🌡️ Temperature (°C)"
          value={temperature}
          setValue={setTemperature}
          hint="Air temperature"
        />

        <InputField
          label="💨 Wind speed (km/h)"
          value={wind}
          setValue={setWind}
          hint="Range: 0–300 km/h"
        />
      </View>

      <TouchableOpacity
        style={[
          styles.runButton,
          loading && styles.disabledButton,
        ]}
        onPress={runSimulation}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#FFFFFF" />
        ) : (
          <Text style={styles.runText}>
            Show Simulated Flood-Risk Zones
          </Text>
        )}
      </TouchableOpacity>

      <View style={styles.bottomSpace} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#F5F3FF",
  },

  header: {
    backgroundColor: "#7C3AED",
    padding: 24,
    paddingTop: 36,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },

  title: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 6,
  },

  subtitle: {
    color: "rgba(255,255,255,0.9)",
    fontSize: 13,
    lineHeight: 19,
  },

  notice: {
    backgroundColor: "#FFFBEB",
    borderColor: "#F59E0B",
    borderWidth: 1,
    margin: 16,
    padding: 13,
    borderRadius: 12,
  },

  noticeTitle: {
    color: "#92400E",
    fontWeight: "800",
    marginBottom: 4,
  },

  noticeText: {
    color: "#92400E",
    fontSize: 12,
    lineHeight: 17,
  },

  quickCard: {
    backgroundColor: "#FFFFFF",
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 16,
    borderRadius: 16,
  },

  card: {
    backgroundColor: "#FFFFFF",
    marginHorizontal: 16,
    marginBottom: 14,
    padding: 16,
    borderRadius: 16,
  },

  cardTitle: {
    color: "#0F172A",
    fontWeight: "700",
    fontSize: 16,
    marginBottom: 14,
  },

  quickRow: {
    flexDirection: "row",
    gap: 8,
  },

  quickButton: {
    flex: 1,
    paddingVertical: 11,
    alignItems: "center",
    borderRadius: 9,
  },

  dry: {
    backgroundColor: "#DCFCE7",
  },

  moderate: {
    backgroundColor: "#FFEDD5",
  },

  heavy: {
    backgroundColor: "#DC2626",
  },

  quickText: {
    fontSize: 12,
    fontWeight: "700",
    color: "#334155",
  },

  field: {
    marginBottom: 15,
  },

  label: {
    color: "#334155",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 6,
  },

  input: {
    borderWidth: 1.5,
    borderColor: "#CBD5E1",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    color: "#0F172A",
  },

  hint: {
    color: "#94A3B8",
    fontSize: 11,
    marginTop: 4,
  },

  runButton: {
    backgroundColor: "#7C3AED",
    marginHorizontal: 16,
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },

  disabledButton: {
    opacity: 0.7,
  },

  runText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "800",
  },

  bottomSpace: {
    height: 40,
  },
});