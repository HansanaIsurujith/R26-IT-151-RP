import React from "react";
import { View, StyleSheet, Text, Pressable, ScrollView } from "react-native";

export default function HomeScreen({ navigation }) {
  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Header Section */}
      <View style={styles.header}>
        <Text style={styles.emoji}>🛡️</Text>
        <Text style={styles.title}>Suraksha Lanka</Text>
        <Text style={styles.subtitle}>Disaster & Wildlife Detection System</Text>
      </View>

      {/* Welcome Message */}
      <View style={styles.welcomeSection}>
        <Text style={styles.welcomeText}>
          Protecting Sri Lanka with Advanced Monitoring Technology
        </Text>
      </View>

      {/* Features Grid */}
      <View style={styles.featuresContainer}>
        <Text style={styles.sectionTitle}>Our Services</Text>

        {/* Flood Feature */}
        <View style={[styles.featureCard, styles.floodCard]}>
          <Text style={styles.featureEmoji}>🌊</Text>
          <Text style={styles.featureName}>Flood Detection</Text>
          <Text style={styles.featureDesc}>
            Real-time flood monitoring and early warnings
          </Text>
        </View>

        {/* Landslide Feature */}
        <View style={[styles.featureCard, styles.landslideCard]}>
          <Text style={styles.featureEmoji}>⛰️</Text>
          <Text style={styles.featureName}>Landslide Detection</Text>
          <Text style={styles.featureDesc}>
            Detect and monitor landslide-prone areas
          </Text>
        </View>

        {/* Wildlife Feature */}
        <View style={[styles.featureCard, styles.wildlifeCard]}>
          <Text style={styles.featureEmoji}>🐘</Text>
          <Text style={styles.featureName}>Wildlife Detection</Text>
          <Text style={styles.featureDesc}>
            Track elephant movement and wildlife patterns
          </Text>
        </View>
      </View>

      {/* Info Section */}
      <View style={styles.infoSection}>
        <View style={styles.infoItem}>
          <Text style={styles.infoIcon}>📍</Text>
          <Text style={styles.infoText}>Real-time Location Tracking</Text>
        </View>
        <View style={styles.infoItem}>
          <Text style={styles.infoIcon}>⚡</Text>
          <Text style={styles.infoText}>Instant Alerts & Notifications</Text>
        </View>
        <View style={styles.infoItem}>
          <Text style={styles.infoIcon}>🗺️</Text>
          <Text style={styles.infoText}>Interactive Map View</Text>
        </View>
      </View>

      {/* CTA Button */}
      <Pressable
        style={({ pressed }) => [
          styles.ctaButton,
          pressed && styles.ctaButtonPressed,
        ]}
        onPress={() => navigation.navigate("Map")}
      >
        <Text style={styles.ctaText}>Start Monitoring</Text>
        <Text style={styles.ctaArrow}>→</Text>
      </Pressable>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Version 1.0.0 • Protecting Lives, Preserving Wildlife
        </Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f0f9ff",
  },
  header: {
    alignItems: "center",
    paddingVertical: 50,
    paddingHorizontal: 20,
    backgroundColor: "#0ea5e9",
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 30,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 8,
  },
  emoji: {
    fontSize: 60,
    marginBottom: 10,
  },
  title: {
    fontSize: 36,
    fontWeight: "800",
    color: "#fff",
    marginBottom: 8,
    letterSpacing: 0.5,
  },
  subtitle: {
    fontSize: 16,
    color: "rgba(255, 255, 255, 0.9)",
    fontWeight: "500",
    textAlign: "center",
  },
  welcomeSection: {
    paddingHorizontal: 20,
    paddingVertical: 30,
    marginTop: -15,
  },
  welcomeText: {
    fontSize: 18,
    fontWeight: "600",
    color: "#0369a1",
    textAlign: "center",
    lineHeight: 26,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#0c4a6e",
    marginBottom: 16,
    marginTop: 10,
  },
  featuresContainer: {
    paddingHorizontal: 20,
    paddingBottom: 10,
  },
  featureCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  floodCard: {
    backgroundColor: "#bfdbfe",
    borderLeftWidth: 4,
    borderLeftColor: "#3b82f6",
  },
  landslideCard: {
    backgroundColor: "#fecaca",
    borderLeftWidth: 4,
    borderLeftColor: "#ef4444",
  },
  wildlifeCard: {
    backgroundColor: "#a7f3d0",
    borderLeftWidth: 4,
    borderLeftColor: "#10b981",
  },
  featureEmoji: {
    fontSize: 40,
    marginBottom: 10,
  },
  featureName: {
    fontSize: 16,
    fontWeight: "700",
    color: "#1f2937",
    marginBottom: 6,
  },
  featureDesc: {
    fontSize: 13,
    color: "#4b5563",
    textAlign: "center",
    lineHeight: 18,
  },
  infoSection: {
    paddingHorizontal: 20,
    paddingVertical: 20,
    gap: 12,
  },
  infoItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: "#fff",
    borderRadius: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  infoIcon: {
    fontSize: 24,
    marginRight: 12,
  },
  infoText: {
    fontSize: 14,
    fontWeight: "600",
    color: "#1f2937",
    flex: 1,
  },
  ctaButton: {
    marginHorizontal: 20,
    marginVertical: 20,
    paddingVertical: 16,
    paddingHorizontal: 20,
    backgroundColor: "#0ea5e9",
    borderRadius: 16,
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#0ea5e9",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  ctaButtonPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  ctaText: {
    fontSize: 18,
    fontWeight: "700",
    color: "#fff",
    marginRight: 8,
  },
  ctaArrow: {
    fontSize: 18,
    color: "#fff",
    fontWeight: "700",
  },
  footer: {
    paddingVertical: 20,
    paddingHorizontal: 20,
    alignItems: "center",
  },
  footerText: {
    fontSize: 12,
    color: "#64748b",
    textAlign: "center",
    fontWeight: "500",
  },
});
