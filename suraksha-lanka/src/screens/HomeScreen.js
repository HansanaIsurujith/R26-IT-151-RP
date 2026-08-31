// import React from "react";
// import { View, StyleSheet, Text, Pressable, ScrollView } from "react-native";

// export default function HomeScreen({ navigation }) {
//   return (
//     <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
//       {/* Header Section */}
//       <View style={styles.header}>
//         <Text style={styles.emoji}>🛡️</Text>
//         <Text style={styles.title}>Suraksha Lanka</Text>
//         <Text style={styles.subtitle}>Disaster & Wildlife Detection System</Text>
//       </View>

//       {/* Welcome Message */}
//       <View style={styles.welcomeSection}>
//         <Text style={styles.welcomeText}>
//           Protecting Sri Lanka with Advanced Monitoring Technology
//         </Text>
//       </View>

//       {/* Features Grid */}
//       <View style={styles.featuresContainer}>
//         <Text style={styles.sectionTitle}>Our Services</Text>

//         {/* Flood Feature */}
//         <View style={[styles.featureCard, styles.floodCard]}>
//           <Text style={styles.featureEmoji}>🌊</Text>
//           <Text style={styles.featureName}>Flood Detection</Text>
//           <Text style={styles.featureDesc}>
//             Real-time flood monitoring and early warnings
//           </Text>
//         </View>

//         {/* Landslide Feature */}
//         <View style={[styles.featureCard, styles.landslideCard]}>
//           <Text style={styles.featureEmoji}>⛰️</Text>
//           <Text style={styles.featureName}>Landslide Detection</Text>
//           <Text style={styles.featureDesc}>
//             Detect and monitor landslide-prone areas
//           </Text>
//         </View>

//         {/* Wildlife Feature */}
//         <View style={[styles.featureCard, styles.wildlifeCard]}>
//           <Text style={styles.featureEmoji}>🐘</Text>
//           <Text style={styles.featureName}>Wildlife Detection</Text>
//           <Text style={styles.featureDesc}>
//             Track elephant movement and wildlife patterns
//           </Text>
//         </View>
//       </View>

//       {/* Info Section */}
//       <View style={styles.infoSection}>
//         <View style={styles.infoItem}>
//           <Text style={styles.infoIcon}>📍</Text>
//           <Text style={styles.infoText}>Real-time Location Tracking</Text>
//         </View>
//         <View style={styles.infoItem}>
//           <Text style={styles.infoIcon}>⚡</Text>
//           <Text style={styles.infoText}>Instant Alerts & Notifications</Text>
//         </View>
//         <View style={styles.infoItem}>
//           <Text style={styles.infoIcon}>🗺️</Text>
//           <Text style={styles.infoText}>Interactive Map View</Text>
//         </View>
//       </View>

//       {/* CTA Button */}
//       <Pressable
//         style={({ pressed }) => [
//           styles.ctaButton,
//           pressed && styles.ctaButtonPressed,
//         ]}
//         onPress={() => navigation.navigate("Map")}
//       >
//         <Text style={styles.ctaText}>Start Monitoring</Text>
//         <Text style={styles.ctaArrow}>→</Text>
//       </Pressable>

//       <Pressable
//         style={styles.ctaButton}
//         onPress={() => navigation.navigate("ManualInput")}
//       >
//         <Text style={styles.ctaText}>📍 Check a Location</Text>
//       </Pressable>

//       <Pressable
//         style={[styles.ctaButton,
//       {
//         backgroundColor: "#7C3AED",},
//       ]}
//         onPress={() =>
//         navigation.navigate("FloodScenario")
//       }
//       >
//       <Text style={styles.ctaText}>
//         🧪 Flood Scenario Simulation
//       </Text>
//       </Pressable>

//       {/* Footer */}
//       <View style={styles.footer}>
//         <Text style={styles.footerText}>
//           Version 1.0.0 • Protecting Lives, Preserving Wildlife
//         </Text>
//       </View>
//     </ScrollView>
//   );
// }

// const styles = StyleSheet.create({
//   container: {
//     flex: 1,
//     backgroundColor: "#f0f9ff",
//   },
//   header: {
//     alignItems: "center",
//     paddingVertical: 50,
//     paddingHorizontal: 20,
//     backgroundColor: "#0ea5e9",
//     borderBottomLeftRadius: 30,
//     borderBottomRightRadius: 30,
//     shadowColor: "#000",
//     shadowOffset: { width: 0, height: 4 },
//     shadowOpacity: 0.15,
//     shadowRadius: 8,
//     elevation: 8,
//   },
//   emoji: {
//     fontSize: 60,
//     marginBottom: 10,
//   },
//   title: {
//     fontSize: 36,
//     fontWeight: "800",
//     color: "#fff",
//     marginBottom: 8,
//     letterSpacing: 0.5,
//   },
//   subtitle: {
//     fontSize: 16,
//     color: "rgba(255, 255, 255, 0.9)",
//     fontWeight: "500",
//     textAlign: "center",
//   },
//   welcomeSection: {
//     paddingHorizontal: 20,
//     paddingVertical: 30,
//     marginTop: -15,
//   },
//   welcomeText: {
//     fontSize: 18,
//     fontWeight: "600",
//     color: "#0369a1",
//     textAlign: "center",
//     lineHeight: 26,
//   },
//   sectionTitle: {
//     fontSize: 22,
//     fontWeight: "700",
//     color: "#0c4a6e",
//     marginBottom: 16,
//     marginTop: 10,
//   },
//   featuresContainer: {
//     paddingHorizontal: 20,
//     paddingBottom: 10,
//   },
//   featureCard: {
//     borderRadius: 16,
//     padding: 20,
//     marginBottom: 12,
//     alignItems: "center",
//     shadowColor: "#000",
//     shadowOffset: { width: 0, height: 2 },
//     shadowOpacity: 0.1,
//     shadowRadius: 4,
//     elevation: 3,
//   },
//   floodCard: {
//     backgroundColor: "#bfdbfe",
//     borderLeftWidth: 4,
//     borderLeftColor: "#3b82f6",
//   },
//   landslideCard: {
//     backgroundColor: "#fecaca",
//     borderLeftWidth: 4,
//     borderLeftColor: "#ef4444",
//   },
//   wildlifeCard: {
//     backgroundColor: "#a7f3d0",
//     borderLeftWidth: 4,
//     borderLeftColor: "#10b981",
//   },
//   featureEmoji: {
//     fontSize: 40,
//     marginBottom: 10,
//   },
//   featureName: {
//     fontSize: 16,
//     fontWeight: "700",
//     color: "#1f2937",
//     marginBottom: 6,
//   },
//   featureDesc: {
//     fontSize: 13,
//     color: "#4b5563",
//     textAlign: "center",
//     lineHeight: 18,
//   },
//   infoSection: {
//     paddingHorizontal: 20,
//     paddingVertical: 20,
//     gap: 12,
//   },
//   infoItem: {
//     flexDirection: "row",
//     alignItems: "center",
//     paddingHorizontal: 16,
//     paddingVertical: 12,
//     backgroundColor: "#fff",
//     borderRadius: 12,
//     shadowColor: "#000",
//     shadowOffset: { width: 0, height: 1 },
//     shadowOpacity: 0.05,
//     shadowRadius: 2,
//     elevation: 1,
//   },
//   infoIcon: {
//     fontSize: 24,
//     marginRight: 12,
//   },
//   infoText: {
//     fontSize: 14,
//     fontWeight: "600",
//     color: "#1f2937",
//     flex: 1,
//   },
//   ctaButton: {
//     marginHorizontal: 20,
//     marginVertical: 20,
//     paddingVertical: 16,
//     paddingHorizontal: 20,
//     backgroundColor: "#0ea5e9",
//     borderRadius: 16,
//     flexDirection: "row",
//     justifyContent: "center",
//     alignItems: "center",
//     shadowColor: "#0ea5e9",
//     shadowOffset: { width: 0, height: 4 },
//     shadowOpacity: 0.3,
//     shadowRadius: 8,
//     elevation: 6,
//   },
//   ctaButtonPressed: {
//     opacity: 0.85,
//     transform: [{ scale: 0.98 }],
//   },
//   ctaText: {
//     fontSize: 18,
//     fontWeight: "700",
//     color: "#fff",
//     marginRight: 8,
//   },
//   ctaArrow: {
//     fontSize: 18,
//     color: "#fff",
//     fontWeight: "700",
//   },
//   footer: {
//     paddingVertical: 20,
//     paddingHorizontal: 20,
//     alignItems: "center",
//   },
//   footerText: {
//     fontSize: 12,
//     color: "#64748b",
//     textAlign: "center",
//     fontWeight: "500",
//   },
// });


import React from "react";
import {
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from "react-native";

const SERVICES = [
  {
    icon: "🌊",
    number: "01",
    title: "Flood Intelligence",
    description:
      "AI-powered flood prediction, live environmental signals and risk-zone visualization.",
    color: "#20D3EE",
    background: "#0A3043",
  },
  {
    icon: "🐘",
    number: "02",
    title: "Wildlife & Road Safety",
    description:
      "Wildlife movement and slippery-area awareness designed for Sri Lankan roads.",
    color: "#56E3A8",
    background: "#12382F",
  },
  {
    icon: "⛽",
    number: "03",
    title: "Fuel Intelligence",
    description:
      "Predictive fuel insights that support efficient and informed travel decisions.",
    color: "#FFBD52",
    background: "#3B301B",
  },
  {
    icon: "🧭",
    number: "04",
    title: "Smart Route Optimization",
    description:
      "Risk-aware route recommendations powered by integrated safety intelligence.",
    color: "#B9A5FF",
    background: "#2C2847",
  },
];

function ServiceCard({ item }) {
  return (
    <View style={[styles.serviceCard, { backgroundColor: item.background }]}> 
      <View style={styles.serviceTop}>
        <View style={[styles.serviceIcon, { borderColor: `${item.color}55` }]}> 
          <Text style={styles.serviceEmoji}>{item.icon}</Text>
        </View>
        <Text style={[styles.serviceNumber, { color: item.color }]}>{item.number}</Text>
      </View>

      <Text style={styles.serviceTitle}>{item.title}</Text>
      <View style={[styles.serviceLine, { backgroundColor: item.color }]} />
      <Text style={styles.serviceDescription}>{item.description}</Text>
    </View>
  );
}

export default function HomeScreen({ navigation }) {
  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor="#041723" />

      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <View style={styles.glowOne} />
          <View style={styles.glowTwo} />

          <View style={styles.topBar}>
            <View style={styles.brandRow}>
              <View style={styles.miniLogoBox}>
                <Image
                  source={require("../../assets/suraksha-logo.png")}
                  style={styles.miniLogo}
                  resizeMode="contain"
                />
              </View>

              <View>
                <Text style={styles.brandName}>Suraksha Lanka</Text>
                <Text style={styles.brandLabel}>AI SAFETY PLATFORM</Text>
              </View>
            </View>

            <View style={styles.liveBadge}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>LIVE</Text>
            </View>
          </View>

          <View style={styles.logoStage}>
            <View style={styles.outerRing}>
              <View style={styles.innerRing}>
                <Image
                  source={require("../../assets/suraksha-logo.png")}
                  style={styles.heroLogo}
                  resizeMode="contain"
                />
              </View>
            </View>
          </View>

          <View style={styles.eyebrow}>
            <Text style={styles.eyebrowText}>✦ RESEARCH-POWERED SAFETY</Text>
          </View>

          <Text style={styles.heroTitle}>
            Intelligence that makes every journey
            <Text style={styles.heroAccent}> safer.</Text>
          </Text>

          <Text style={styles.heroDescription}>
            One intelligent platform for disaster prediction, wildlife
            awareness, fuel insights and risk-aware route optimization.
          </Text>

          <Pressable
            style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]}
            onPress={() => navigation.navigate("Map")}
          >
            <Text style={styles.primaryButtonText}>Open Safety Map</Text>
            <Text style={styles.primaryArrow}>→</Text>
          </Pressable>

          <View style={styles.metricsRow}>
            <View style={styles.metric}>
              <Text style={styles.metricValue}>4</Text>
              <Text style={styles.metricLabel}>AI SYSTEMS</Text>
            </View>
            <View style={styles.metricDivider} />
            <View style={styles.metric}>
              <Text style={styles.metricValue}>LIVE</Text>
              <Text style={styles.metricLabel}>RISK SIGNALS</Text>
            </View>
            <View style={styles.metricDivider} />
            <View style={styles.metric}>
              <Text style={styles.metricValue}>LK</Text>
              <Text style={styles.metricLabel}>LOCAL FOCUS</Text>
            </View>
          </View>
        </View>

        <View style={styles.bodySection}>
          <Text style={styles.sectionEyebrow}>THE INTELLIGENT PLATFORM</Text>
          <Text style={styles.sectionTitle}>Four systems. One safer Sri Lanka.</Text>
          <Text style={styles.sectionDescription}>
            Each research component solves a focused challenge. Together they
            create a connected decision layer for safer travel.
          </Text>

          <View style={styles.servicesGrid}>
            {SERVICES.map((item) => (
              <ServiceCard key={item.number} item={item} />
            ))}
          </View>

          <View style={styles.actionPanel}>
            <Text style={styles.actionEyebrow}>FLOOD RISK COMPONENT</Text>
            <Text style={styles.actionTitle}>Explore live risk or simulate a scenario.</Text>
            <Text style={styles.actionDescription}>
              Check location-level flood risk using live weather or test how
              hypothetical weather values influence predicted risk zones.
            </Text>

            <Pressable
              style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}
              onPress={() => navigation.navigate("ManualInput")}
            >
              <Text style={styles.actionButtonText}>📍 Check Flood Risk</Text>
              <Text style={styles.actionButtonArrow}>→</Text>
            </Pressable>

            <Pressable
              style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}
              onPress={() => navigation.navigate("FloodScenario")}
            >
              <Text style={styles.secondaryButtonText}>🧪 Run Scenario Simulation</Text>
            </Pressable>
          </View>
                    <Pressable
            accessibilityRole="button"
            accessibilityLabel="Open risk-aware route optimization"
            style={({ pressed }) => [
              styles.routeButton,
              pressed && styles.pressed,
            ]}
            onPress={() =>
              navigation.navigate(
                "RouteOptimization",
              )
            }
          >
            <View>
              <Text style={styles.routeLabel}>
                SMART ROUTING
              </Text>

              <Text style={styles.routeTitle}>
                🧭 Open Risk-Aware Route Planner
              </Text>
            </View>

            <Text style={styles.routeArrow}>
              →
            </Text>
          </Pressable>

          <View style={styles.missionCard}>
            <View style={styles.missionIcon}><Text style={styles.missionEmoji}>🛡️</Text></View>
            <Text style={styles.missionLabel}>OUR RESEARCH MISSION</Text>
            <Text style={styles.missionTitle}>Better foresight. Safer movement.</Text>
            <Text style={styles.missionText}>
              Real-time insights, early warnings and optimized travel solutions
              built using AI, environmental data and map-based technologies.
            </Text>
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerBrand}>SURAKSHA LANKA</Text>
            <Text style={styles.footerText}>Research Prototype • Version 1.0.0</Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#041723" },
  container: { flex: 1, backgroundColor: "#F3F8F8" },
  content: { paddingBottom: 0 },
  hero: { backgroundColor: "#041C2A", paddingHorizontal: 20, paddingTop: 14, paddingBottom: 34, overflow: "hidden", borderBottomLeftRadius: 34, borderBottomRightRadius: 34 },
  glowOne: { position: "absolute", width: 260, height: 260, borderRadius: 130, backgroundColor: "rgba(26, 201, 232, 0.11)", right: -90, top: 70 },
  glowTwo: { position: "absolute", width: 190, height: 190, borderRadius: 95, backgroundColor: "rgba(56, 200, 131, 0.08)", left: -100, bottom: 70 },
  topBar: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  miniLogoBox: { width: 46, height: 46, borderRadius: 14, backgroundColor: "rgba(255,255,255,0.08)", borderWidth: 1, borderColor: "rgba(255,255,255,0.12)", alignItems: "center", justifyContent: "center" },
  miniLogo: { width: 40, height: 40 },
  brandName: { color: "#FFFFFF", fontSize: 15, fontWeight: "800" },
  brandLabel: { color: "#76AAB7", fontSize: 8, letterSpacing: 1.5, marginTop: 2, fontWeight: "700" },
  liveBadge: { flexDirection: "row", alignItems: "center", gap: 7, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 20, backgroundColor: "rgba(69,225,158,0.08)", borderWidth: 1, borderColor: "rgba(69,225,158,0.24)" },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: "#45E19E" },
  liveText: { color: "#8EEAC0", fontSize: 9, fontWeight: "900", letterSpacing: 1.1 },
  logoStage: { alignItems: "center", marginTop: 26, marginBottom: 16 },
  outerRing: { width: 235, height: 235, borderRadius: 118, borderWidth: 1, borderColor: "rgba(72,212,226,0.17)", alignItems: "center", justifyContent: "center" },
  innerRing: { width: 195, height: 195, borderRadius: 98, backgroundColor: "rgba(15,69,86,0.36)", borderWidth: 1, borderColor: "rgba(79,220,225,0.16)", alignItems: "center", justifyContent: "center" },
  heroLogo: { width: 184, height: 184 },
  eyebrow: { alignSelf: "center", paddingHorizontal: 12, paddingVertical: 7, borderRadius: 18, backgroundColor: "rgba(32,211,238,0.08)", borderWidth: 1, borderColor: "rgba(32,211,238,0.22)" },
  eyebrowText: { color: "#77DEEC", fontSize: 9, fontWeight: "800", letterSpacing: 1.1 },
  heroTitle: { color: "#FFFFFF", fontSize: 39, lineHeight: 42, letterSpacing: -1.5, fontWeight: "900", textAlign: "center", marginTop: 22 },
  heroAccent: { color: "#51DDA5" },
  heroDescription: { color: "#9BBAC3", textAlign: "center", fontSize: 14, lineHeight: 22, marginTop: 18, paddingHorizontal: 8 },
  primaryButton: { height: 56, backgroundColor: "#46D9A3", borderRadius: 18, marginTop: 28, flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 12 },
  primaryButtonText: { color: "#052535", fontSize: 15, fontWeight: "900" },
  primaryArrow: { color: "#052535", fontSize: 21, fontWeight: "800" },
  pressed: { opacity: 0.82, transform: [{ scale: 0.985 }] },
  metricsRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-around", marginTop: 30, paddingTop: 24, borderTopWidth: 1, borderTopColor: "rgba(255,255,255,0.1)" },
  metric: { flex: 1, alignItems: "center" },
  metricValue: { color: "#EAF8F9", fontSize: 16, fontWeight: "900" },
  metricLabel: { color: "#688F9B", fontSize: 7, letterSpacing: 1, marginTop: 4, fontWeight: "700" },
  metricDivider: { width: 1, height: 30, backgroundColor: "rgba(255,255,255,0.1)" },
  bodySection: { paddingHorizontal: 16, paddingTop: 60 },
  sectionEyebrow: { color: "#0A8BA6", fontSize: 9, letterSpacing: 1.6, fontWeight: "900" },
  sectionTitle: { color: "#082432", fontSize: 32, lineHeight: 36, fontWeight: "900", letterSpacing: -1, marginTop: 12 },
  sectionDescription: { color: "#62777F", fontSize: 13, lineHeight: 21, marginTop: 14 },
  servicesGrid: { marginTop: 26, gap: 12 },
  serviceCard: { padding: 22, borderRadius: 24, minHeight: 220 },
  serviceTop: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  serviceIcon: { width: 48, height: 48, borderRadius: 15, borderWidth: 1, backgroundColor: "rgba(255,255,255,0.06)", alignItems: "center", justifyContent: "center" },
  serviceEmoji: { fontSize: 23 },
  serviceNumber: { fontSize: 10, letterSpacing: 1.3, fontWeight: "900" },
  serviceTitle: { color: "#FFFFFF", fontSize: 20, fontWeight: "900", marginTop: 25 },
  serviceLine: { width: 32, height: 3, borderRadius: 2, marginTop: 14, marginBottom: 14 },
  serviceDescription: { color: "#A6BEC5", fontSize: 12, lineHeight: 19 },
  actionPanel: { backgroundColor: "#FFFFFF", borderRadius: 28, padding: 24, marginTop: 48, borderWidth: 1, borderColor: "#DCE9EA" },
  actionEyebrow: { color: "#0B94AD", fontSize: 9, letterSpacing: 1.4, fontWeight: "900" },
  actionTitle: { color: "#092635", fontSize: 27, lineHeight: 31, fontWeight: "900", letterSpacing: -0.6, marginTop: 13 },
  actionDescription: { color: "#687D85", fontSize: 13, lineHeight: 20, marginTop: 13 },
  actionButton: { height: 54, borderRadius: 16, backgroundColor: "#0B7898", flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 18, marginTop: 24 },
  actionButtonText: { color: "#FFFFFF", fontSize: 14, fontWeight: "900" },
  actionButtonArrow: { color: "#FFFFFF", fontSize: 20 },
  secondaryButton: { height: 54, borderRadius: 16, backgroundColor: "#EBF5F5", alignItems: "center", justifyContent: "center", marginTop: 10 },
  secondaryButtonText: { color: "#164151", fontSize: 14, fontWeight: "800" },
    routeButton: {
    minHeight: 74,
    marginTop: 12,
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: "#0F766E",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },

  routeLabel: {
    color: "#99F6E4",
    fontSize: 8,
    fontWeight: "900",
    letterSpacing: 1.3,
    marginBottom: 5,
  },

  routeTitle: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "900",
  },

  routeArrow: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "800",
  },
  missionCard: { backgroundColor: "#0B536D", borderRadius: 28, padding: 26, marginTop: 18 },
  missionIcon: { width: 58, height: 58, borderRadius: 18, backgroundColor: "rgba(255,255,255,0.1)", borderWidth: 1, borderColor: "rgba(255,255,255,0.15)", alignItems: "center", justifyContent: "center" },
  missionEmoji: { fontSize: 28 },
  missionLabel: { color: "#78E5C1", fontSize: 9, letterSpacing: 1.4, fontWeight: "900", marginTop: 24 },
  missionTitle: { color: "#FFFFFF", fontSize: 27, lineHeight: 32, fontWeight: "900", letterSpacing: -0.7, marginTop: 11 },
  missionText: { color: "#B7D2DA", fontSize: 13, lineHeight: 21, marginTop: 13 },
  footer: { alignItems: "center", paddingVertical: 38 },
  footerBrand: { color: "#173D4B", fontSize: 11, letterSpacing: 2, fontWeight: "900" },
  footerText: { color: "#8A9BA1", fontSize: 10, marginTop: 7 },
});
