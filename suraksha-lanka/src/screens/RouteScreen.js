/**
 * Modern map-first UI for the Suraksha Lanka Option B routing component.
 * It reuses the application's existing react-native-maps provider while
 * keeping all route state and API calls isolated from MapScreen.
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Modal,
  Platform,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import * as Location from "expo-location";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  formatCoordinate,
  getHazardStatus,
  getRouteHealth,
  getRouteRiskColor,
  getRouteRiskLabel,
  optimizeRoute,
  reverseLocation,
  ROUTE_API_BASE_URL,
  searchLocations,
} from "../services/routeApi";

let MapView = null;
let Marker = null;
let Polyline = null;
let PROVIDER_GOOGLE = null;
let mapModuleAvailable = false;

if (Platform.OS !== "web") {
  try {
    const mapPackage = require("react-native-maps");
    MapView = mapPackage.default || mapPackage;
    Marker = mapPackage.Marker;
    Polyline = mapPackage.Polyline;
    PROVIDER_GOOGLE = mapPackage.PROVIDER_GOOGLE;
    mapModuleAvailable = true;
  } catch (mapError) {
    console.warn("Route map unavailable:", mapError.message);
  }
}

const COLORS = {
  primary: "#0EA5E9",
  primaryDark: "#0369A1",
  navy: "#0F172A",
  slate: "#475569",
  muted: "#64748B",
  line: "#E2E8F0",
  surface: "#FFFFFF",
  softBlue: "#F0F9FF",
  success: "#16A34A",
  danger: "#DC2626",
};

const GAMPAHA_CENTER = { latitude: 7.08, longitude: 80.01 };
const DEFAULT_ORIGIN = {
  latitude: 7.0917,
  longitude: 79.9942,
  label: "Gampaha",
};
const DEFAULT_DESTINATION = {
  latitude: 7.1447,
  longitude: 80.096,
  label: "Nittambuwa",
};

const METHOD_OPTIONS = [
  {
    id: "objective_fuzzy",
    icon: "🛡️",
    short: "Risk Aware",
    detail: "Proposed model",
  },
  {
    id: "objective_weight",
    icon: "⚖️",
    short: "Objective",
    detail: "Linear baseline",
  },
  {
    id: "shortest_path",
    icon: "⚡",
    short: "Fastest",
    detail: "Time only",
  },
];

const RISK_PROFILES = [
  { value: 4, label: "Flexible" },
  { value: 8, label: "Balanced" },
  { value: 12, label: "Safety first" },
];

const HAZARD_LABELS = {
  flood: "Flood",
  landslide: "Landslide",
  elephant: "Elephant",
  buffalo: "Buffalo",
  deer: "Deer",
  wildboar: "Wild boar",
};

const HAZARD_ICONS = {
  flood: "🌊",
  landslide: "⛰️",
  elephant: "🐘",
  buffalo: "🐃",
  deer: "🦌",
  wildboar: "🐗",
};

function riskTint(level) {
  if (level === "low") return "#DCFCE7";
  if (level === "moderate") return "#FEF3C7";
  if (level === "high") return "#FFEDD5";
  return "#FEE2E2";
}

function qualityTint(level) {
  if (level === "high") return { background: "#DCFCE7", text: "#166534" };
  if (level === "moderate") return { background: "#FEF3C7", text: "#92400E" };
  return { background: "#FEE2E2", text: "#991B1B" };
}

function formatDuration(minutes) {
  if (minutes < 60) return Math.max(1, Math.round(minutes)) + " min";
  const hours = Math.floor(minutes / 60);
  const remainder = Math.round(minutes % 60);
  return hours + "h " + remainder + "m";
}

function formatSigned(value, suffix) {
  if (Math.abs(value) < 0.05) return "0" + suffix;
  return (value > 0 ? "+" : "") + value.toFixed(1) + suffix;
}

function methodIcon(method) {
  return METHOD_OPTIONS.find((item) => item.id === method)?.icon || "🧭";
}

function RouteMarker({ type }) {
  const isOrigin = type === "origin";
  return (
    <View
      style={[
        styles.markerHalo,
        { backgroundColor: isOrigin ? "rgba(22,163,74,0.18)" : "rgba(220,38,38,0.18)" },
      ]}
    >
      <View
        style={[
          styles.markerCore,
          { backgroundColor: isOrigin ? COLORS.success : COLORS.danger },
        ]}
      >
        <Text style={styles.markerText}>{isOrigin ? "A" : "B"}</Text>
      </View>
    </View>
  );
}

export default function RouteScreen() {
  const insets = useSafeAreaInsets();
  const mapRef = useRef(null);
  const [origin, setOrigin] = useState(DEFAULT_ORIGIN);
  const [destination, setDestination] = useState(DEFAULT_DESTINATION);
  const [originText, setOriginText] = useState(DEFAULT_ORIGIN.label);
  const [destinationText, setDestinationText] = useState(DEFAULT_DESTINATION.label);
  const [locationMatches, setLocationMatches] = useState([]);
  const [isSearchingLocations, setIsSearchingLocations] = useState(false);
  const [selectionMode, setSelectionMode] = useState(null);
  const [method, setMethod] = useState("objective_fuzzy");
  const [riskAversion, setRiskAversion] = useState(8);
  const [userLocation, setUserLocation] = useState(null);
  const [mapReady, setMapReady] = useState(false);
  const [apiState, setApiState] = useState("checking");
  const [apiMeta, setApiMeta] = useState(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [routeResult, setRouteResult] = useState(null);
  const [plannerExpanded, setPlannerExpanded] = useState(true);
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [error, setError] = useState(null);
  const [liveRefreshMessage, setLiveRefreshMessage] = useState(null);
  const liveRefreshBusy = useRef(false);

  useEffect(() => {
    let mounted = true;
    getRouteHealth()
      .then((health) => {
        if (!mounted) return;
        setApiState("online");
        setApiMeta(health);
      })
      .catch(() => {
        if (mounted) setApiState("offline");
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!selectionMode) {
      setLocationMatches([]);
      return undefined;
    }
    const query = selectionMode === "origin" ? originText : destinationText;
    let active = true;
    const timer = setTimeout(() => {
      setIsSearchingLocations(true);
      searchLocations(query)
        .then((matches) => {
          if (active) setLocationMatches(matches);
        })
        .catch(() => {
          if (active) setLocationMatches([]);
        })
        .finally(() => {
          if (active) setIsSearchingLocations(false);
        });
    }, query.trim() ? 250 : 0);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selectionMode, originText, destinationText]);

  const route = routeResult?.route;
  const topHazards = useMemo(() => {
    if (!route) return [];
    return Object.entries(route.hazard_summary)
      .sort((first, second) => second[1] - first[1])
      .slice(0, 3);
  }, [route]);

  const severeSegments = useMemo(() => {
    if (!route) return [];
    return [...route.segments]
      .sort((first, second) => second.risk_score - first.risk_score)
      .slice(0, 5);
  }, [route]);

  const clearRoute = () => {
    setRouteResult(null);
    setError(null);
    setPlannerExpanded(true);
    setLiveRefreshMessage(null);
  };

  const updatePoint = (pointType, coordinate, label) => {
    const nextPoint = { ...coordinate, label };
    if (pointType === "origin") {
      setOrigin(nextPoint);
      setOriginText(label || "Selected origin");
    } else {
      setDestination(nextPoint);
      setDestinationText(label || "Selected destination");
    }
    setRouteResult(null);
    setError(null);
  };

  const changeLocationText = (pointType, text) => {
    if (pointType === "origin") {
      setOriginText(text);
      setOrigin(null);
    } else {
      setDestinationText(text);
      setDestination(null);
    }
    setSelectionMode(pointType);
    setRouteResult(null);
    setError(null);
  };

  const selectLocation = (pointType, place) => {
    updatePoint(pointType, place, place.label);
    setSelectionMode(null);
    setLocationMatches([]);
    mapRef.current?.animateToRegion(
      { ...place, latitudeDelta: 0.08, longitudeDelta: 0.08 },
      450
    );
  };

  const handleMapPress = (event) => {
    if (!selectionMode) return;
    const pointType = selectionMode;
    const coordinate = event.nativeEvent.coordinate;
    updatePoint(pointType, coordinate, "Finding nearby name...");
    setSelectionMode(selectionMode === "origin" ? "destination" : null);
    reverseLocation(coordinate)
      .then((place) => updatePoint(pointType, coordinate, place.label))
      .catch(() => updatePoint(pointType, coordinate, "Selected map location"));
  };

  const useCurrentLocation = async () => {
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (permission.status !== "granted") {
        Alert.alert(
          "Location permission needed",
          "Allow location access to use your current position as the origin."
        );
        return;
      }
      const position = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      });
      const coordinate = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };
      setUserLocation(coordinate);
      updatePoint("origin", coordinate, "Current location");
      reverseLocation(coordinate)
        .then((place) => updatePoint("origin", coordinate, place.label))
        .catch(() => undefined);
      mapRef.current?.animateToRegion(
        { ...coordinate, latitudeDelta: 0.08, longitudeDelta: 0.08 },
        500
      );
    } catch {
      Alert.alert("Location unavailable", "Your current location could not be read.");
    }
  };

  const swapPoints = () => {
    setOrigin(destination);
    setDestination(origin);
    setOriginText(destination?.label || "Selected origin");
    setDestinationText(origin?.label || "Selected destination");
    setRouteResult(null);
    setError(null);
  };

  const chooseMethod = (nextMethod) => {
    setMethod(nextMethod);
    setRouteResult(null);
    setError(null);
  };

  const calculateRoute = async () => {
    if (!origin || !destination) {
      Alert.alert(
        "Choose both locations",
        "Type a place or road name, then select a result from the list. You can also choose a point on the map."
      );
      return;
    }
    if (
      Math.abs(origin.latitude - destination.latitude) < 0.000001 &&
      Math.abs(origin.longitude - destination.longitude) < 0.000001
    ) {
      Alert.alert("Choose two points", "Origin and destination cannot be the same.");
      return;
    }

    setSelectionMode(null);
    setIsOptimizing(true);
    setError(null);
    try {
      const response = await optimizeRoute({
        origin,
        destination,
        method,
        risk_aversion: method === "shortest_path" ? 0 : riskAversion,
        include_comparison: true,
      });
      setOrigin(response.origin);
      setDestination(response.destination);
      setOriginText(response.origin.label || "Selected origin");
      setDestinationText(response.destination.label || "Selected destination");
      setRouteResult(response);
      setLiveRefreshMessage(null);
      setPlannerExpanded(false);
      setApiState("online");
      setApiMeta((current) => ({
        ...(current || {}),
        network: response.network,
      }));

      setTimeout(() => {
        if (response.route.coordinates.length > 1) {
          mapRef.current?.fitToCoordinates(response.route.coordinates, {
            edgePadding: {
              top: 120,
              right: 55,
              bottom: 245 + insets.bottom,
              left: 55,
            },
            animated: true,
          });
        }
      }, 180);
    } catch (routeError) {
      setRouteResult(null);
      setError(routeError.message || "The route could not be calculated.");
      if (routeError.code === "NETWORK_ERROR") setApiState("offline");
    } finally {
      setIsOptimizing(false);
    }
  };

  useEffect(() => {
    if (!routeResult || !origin || !destination) return undefined;
    let active = true;
    const interval = setInterval(async () => {
      if (liveRefreshBusy.current) return;
      try {
        const status = await getHazardStatus();
        if (
          !active ||
          status.hazard_version <= routeResult.network.hazard_version
        ) {
          return;
        }
        liveRefreshBusy.current = true;
        const refreshed = await optimizeRoute({
          origin,
          destination,
          method,
          risk_aversion: method === "shortest_path" ? 0 : riskAversion,
          include_comparison: true,
        });
        if (!active) return;
        setRouteResult(refreshed);
        setApiMeta((current) => ({ ...(current || {}), network: refreshed.network }));
        setLiveRefreshMessage(
          "Live hazard update applied • data v" + refreshed.network.hazard_version
        );
      } catch {
        // Keep the last valid route visible; the normal status control handles outages.
      } finally {
        liveRefreshBusy.current = false;
      }
    }, 8_000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [routeResult, origin, destination, method, riskAversion]);

  const retryConnection = () => {
    setApiState("checking");
    setError(null);
    getRouteHealth()
      .then((health) => {
        setApiState("online");
        setApiMeta(health);
      })
      .catch(() => setApiState("offline"));
  };

  const shareRoute = async () => {
    if (!routeResult) return;
    const selected = routeResult.route;
    const message =
      "Suraksha Lanka risk-aware route\n" +
      formatDuration(selected.duration_min) +
      " • " +
      selected.distance_km.toFixed(1) +
      " km • " +
      getRouteRiskLabel(selected.risk_level) +
      " risk (" +
      Math.round(selected.risk_score * 100) +
      "%)\n" +
      routeResult.recommendation;
    await Share.share({ message });
  };

  if (!mapModuleAvailable) {
    return (
      <View style={styles.placeholder}>
        <Text style={styles.placeholderIcon}>🗺️</Text>
        <Text style={styles.placeholderTitle}>Native map required</Text>
        <Text style={styles.placeholderText}>
          Open this screen in Expo Go on Android or iOS.
        </Text>
      </View>
    );
  }

  const selectedProfile =
    RISK_PROFILES.find((profile) => profile.value === riskAversion) ||
    RISK_PROFILES[1];
  const statusText =
    apiState === "online"
      ? "Live • data v" + (apiMeta?.network?.hazard_version || 1)
      : apiState === "checking"
      ? "Connecting"
      : "Offline";

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_GOOGLE}
        initialRegion={{
          ...GAMPAHA_CENTER,
          latitudeDelta: 0.5,
          longitudeDelta: 0.5,
        }}
        showsUserLocation={Boolean(userLocation)}
        showsMyLocationButton={false}
        showsCompass={false}
        onMapReady={() => setMapReady(true)}
        onPress={handleMapPress}
      >
        {route?.coordinates?.length > 1 && (
          <Polyline
            coordinates={route.coordinates}
            strokeColor="rgba(255,255,255,0.98)"
            strokeWidth={9}
          />
        )}
        {route?.risk_sections
          ?.filter((section) => section.coordinates.length > 1)
          .map((section, index) => (
            <Polyline
              key={"route-risk-" + index}
              coordinates={section.coordinates}
              strokeColor={getRouteRiskColor(section.risk_level)}
              strokeWidth={5.5}
              lineCap="round"
              lineJoin="round"
            />
          ))}
        {origin && Marker && (
          <Marker
            coordinate={origin}
            title={origin.label || "Origin"}
            description="Route starting point"
          >
            <RouteMarker type="origin" />
          </Marker>
        )}
        {destination && Marker && (
          <Marker
            coordinate={destination}
            title={destination.label || "Destination"}
            description="Route destination"
          >
            <RouteMarker type="destination" />
          </Marker>
        )}
      </MapView>

      {!mapReady && (
        <View style={styles.mapLoading}>
          <ActivityIndicator color={COLORS.primary} />
          <Text style={styles.mapLoadingText}>Loading map</Text>
        </View>
      )}

      {plannerExpanded ? (
        <View style={styles.plannerCard}>
          <View style={styles.plannerHeader}>
            <View style={styles.titleWrap}>
              <Text style={styles.eyebrow}>MULTI-HAZARD DECISION SUPPORT</Text>
              <Text style={styles.title}>Choose a lower-risk route</Text>
            </View>
            <TouchableOpacity
              style={styles.statusPill}
              onPress={apiState === "offline" ? retryConnection : undefined}
              activeOpacity={0.8}
            >
              <View
                style={[
                  styles.statusDot,
                  apiState === "online"
                    ? styles.statusOnline
                    : apiState === "checking"
                    ? styles.statusChecking
                    : styles.statusOffline,
                ]}
              />
              <Text style={styles.statusText}>{statusText}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.locationBlock}>
            <View
              style={[
                styles.locationRow,
                selectionMode === "origin" && styles.locationRowActive,
              ]}
            >
              <View style={[styles.locationDot, styles.originDot]} />
              <View style={styles.locationInputWrap}>
                <Text style={styles.locationLabel}>FROM</Text>
                <TextInput
                  value={originText}
                  onChangeText={(text) => changeLocationText("origin", text)}
                  onFocus={() => setSelectionMode("origin")}
                  selectTextOnFocus
                  style={styles.locationInput}
                  placeholder="Search a town or road"
                  placeholderTextColor="#94A3B8"
                />
              </View>
              <TouchableOpacity
                style={styles.iconButton}
                onPress={useCurrentLocation}
                accessibilityLabel="Use current location"
              >
                <Text style={styles.iconButtonText}>◎</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.locationConnector} />
            <View
              style={[
                styles.locationRow,
                selectionMode === "destination" && styles.locationRowActive,
              ]}
            >
              <View style={[styles.locationDot, styles.destinationDot]} />
              <View style={styles.locationInputWrap}>
                <Text style={styles.locationLabel}>TO</Text>
                <TextInput
                  value={destinationText}
                  onChangeText={(text) => changeLocationText("destination", text)}
                  onFocus={() => setSelectionMode("destination")}
                  selectTextOnFocus
                  style={styles.locationInput}
                  placeholder="Search a town or road"
                  placeholderTextColor="#94A3B8"
                />
              </View>
              <TouchableOpacity
                style={styles.iconButton}
                onPress={() => setSelectionMode("destination")}
                accessibilityLabel="Choose destination on map"
              >
                <Text style={styles.pinButtonText}>⌖</Text>
              </TouchableOpacity>
            </View>
            <TouchableOpacity
              style={styles.swapButton}
              onPress={swapPoints}
              accessibilityLabel="Swap origin and destination"
            >
              <Text style={styles.swapText}>⇅</Text>
            </TouchableOpacity>
          </View>

          {selectionMode && (
            <View style={styles.locationResults}>
              <View style={styles.locationResultsHeader}>
                <Text style={styles.locationResultsTitle}>
                  {isSearchingLocations ? "Searching places..." : "Choose a matching place"}
                </Text>
                <TouchableOpacity onPress={() => setSelectionMode(null)}>
                  <Text style={styles.locationResultsClose}>Close</Text>
                </TouchableOpacity>
              </View>
              {locationMatches.length > 0 ? (
                locationMatches.slice(0, 5).map((place) => (
                  <TouchableOpacity
                    key={place.source + place.label + place.latitude + place.longitude}
                    style={styles.locationResultRow}
                    onPress={() => selectLocation(selectionMode, place)}
                  >
                    <Text style={styles.locationResultIcon}>
                      {place.source === "road" ? "↗" : "●"}
                    </Text>
                    <View style={styles.locationResultCopy}>
                      <Text style={styles.locationResultName} numberOfLines={1}>
                        {place.label}
                      </Text>
                      <Text style={styles.locationResultMeta} numberOfLines={1}>
                        {place.secondary_label}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))
              ) : !isSearchingLocations ? (
                <Text style={styles.locationEmpty}>
                  No matching Gampaha place. Try a nearby town or select the map.
                </Text>
              ) : null}
            </View>
          )}

          <View style={styles.methodRow}>
            {METHOD_OPTIONS.map((option) => {
              const active = method === option.id;
              return (
                <TouchableOpacity
                  key={option.id}
                  style={[styles.methodChip, active && styles.methodChipActive]}
                  onPress={() => chooseMethod(option.id)}
                  activeOpacity={0.8}
                >
                  <Text style={styles.methodIcon}>{option.icon}</Text>
                  <Text
                    style={[
                      styles.methodName,
                      active && styles.methodNameActive,
                    ]}
                  >
                    {option.short}
                  </Text>
                  <Text
                    style={[
                      styles.methodDetail,
                      active && styles.methodDetailActive,
                    ]}
                  >
                    {option.detail}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          {method !== "shortest_path" && (
            <View style={styles.preferenceRow}>
              <Text style={styles.preferenceLabel}>Safety preference</Text>
              <View style={styles.preferenceChips}>
                {RISK_PROFILES.map((profile) => (
                  <TouchableOpacity
                    key={profile.value}
                    style={[
                      styles.preferenceChip,
                      riskAversion === profile.value &&
                        styles.preferenceChipActive,
                    ]}
                    onPress={() => {
                      setRiskAversion(profile.value);
                      setRouteResult(null);
                    }}
                  >
                    <Text
                      style={[
                        styles.preferenceText,
                        riskAversion === profile.value &&
                          styles.preferenceTextActive,
                      ]}
                    >
                      {profile.label}
                    </Text>
                  </TouchableOpacity>
                ))}
              </View>
            </View>
          )}

          <TouchableOpacity
            style={[
              styles.calculateButton,
              isOptimizing && styles.calculateButtonDisabled,
            ]}
            onPress={calculateRoute}
            disabled={isOptimizing}
            activeOpacity={0.85}
          >
            {isOptimizing ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.calculateIcon}>✦</Text>
            )}
            <Text style={styles.calculateText}>
              {isOptimizing ? "Evaluating road network..." : "Find best route"}
            </Text>
          </TouchableOpacity>

          {selectionMode && (
            <Text style={styles.selectionHint}>
              Search by name above, or tap the map to set the {selectionMode}.
            </Text>
          )}
        </View>
      ) : (
        <TouchableOpacity
          style={styles.compactPlanner}
          onPress={() => setPlannerExpanded(true)}
          activeOpacity={0.9}
        >
          <View style={styles.compactRouteLine}>
            <View style={[styles.locationDot, styles.originDot]} />
            <Text style={styles.compactLocation} numberOfLines={1}>
              {origin.label || formatCoordinate(origin)}
            </Text>
            <Text style={styles.compactArrow}>→</Text>
            <View style={[styles.locationDot, styles.destinationDot]} />
            <Text style={styles.compactLocation} numberOfLines={1}>
              {destination.label || formatCoordinate(destination)}
            </Text>
          </View>
          <View style={styles.compactEdit}>
            <Text style={styles.compactEditText}>Edit</Text>
          </View>
        </TouchableOpacity>
      )}

      {route && !plannerExpanded && (
        <View style={[styles.summaryCard, { bottom: 14 + insets.bottom }]}>
          <View style={styles.summaryHandle} />
          <View style={styles.summaryHeader}>
            <View style={styles.summaryTitleWrap}>
              <Text style={styles.summaryKicker}>
                {methodIcon(route.method)} {route.method_label}
              </Text>
              <Text style={styles.summaryTitle}>
                {formatDuration(route.duration_min)}
                <Text style={styles.summaryTitleMuted}>
                  {"  •  " + route.distance_km.toFixed(1) + " km"}
                </Text>
              </Text>
            </View>
            <View
              style={[
                styles.riskBadge,
                { backgroundColor: riskTint(route.risk_level) },
              ]}
            >
              <Text
                style={[
                  styles.riskBadgeValue,
                  { color: getRouteRiskColor(route.risk_level) },
                ]}
              >
                {Math.round(route.risk_score * 100)}%
              </Text>
              <Text
                style={[
                  styles.riskBadgeLabel,
                  { color: getRouteRiskColor(route.risk_level) },
                ]}
              >
                {getRouteRiskLabel(route.risk_level)} risk
              </Text>
            </View>
          </View>

          {route.same_as_fastest && route.method !== "shortest_path" && (
            <View style={styles.sameRouteNotice}>
              <Text style={styles.sameRouteIcon}>✓</Text>
              <View style={styles.sameRouteCopy}>
                <Text style={styles.sameRouteTitle}>Same road path as Fastest</Text>
                <Text style={styles.sameRouteText}>
                  No distinct lower-exposure route was selected within the 30% detour limit.
                </Text>
              </View>
            </View>
          )}

          {liveRefreshMessage && (
            <View style={styles.liveRefreshNotice}>
              <View style={styles.liveRefreshDot} />
              <Text style={styles.liveRefreshText}>{liveRefreshMessage}</Text>
            </View>
          )}

          <View style={styles.insightStrip}>
            <View style={styles.insightItem}>
              <Text style={styles.insightValue}>
                {route.risk_reduction_vs_fastest_pct > 0
                  ? "↓ " + route.risk_reduction_vs_fastest_pct.toFixed(1) + "%"
                  : "Similar"}
              </Text>
              <Text style={styles.insightLabel}>exposure vs fastest</Text>
            </View>
            <View style={styles.insightDivider} />
            <View style={styles.insightItem}>
              <Text style={styles.insightValue}>
                {formatSigned(route.time_overhead_vs_fastest_pct, "%")}
              </Text>
              <Text style={styles.insightLabel}>travel-time change</Text>
            </View>
            <View style={styles.insightDivider} />
            <View style={styles.insightItem}>
              <Text style={styles.insightValue}>{route.high_risk_segments}</Text>
              <Text style={styles.insightLabel}>critical sections</Text>
            </View>
          </View>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.topHazards}
          >
            {topHazards.map(([name, score]) => (
              <View style={styles.hazardPill} key={name}>
                <Text style={styles.hazardPillText}>
                  {HAZARD_ICONS[name]} {HAZARD_LABELS[name]}{" "}
                  {Math.round(score * 100)}%
                </Text>
              </View>
            ))}
          </ScrollView>

          <View style={styles.summaryActions}>
            <TouchableOpacity style={styles.secondaryButton} onPress={clearRoute}>
              <Text style={styles.secondaryButtonText}>New route</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.analysisButton}
              onPress={() => setAnalysisVisible(true)}
            >
              <Text style={styles.analysisButtonText}>View full analysis</Text>
              <Text style={styles.analysisButtonArrow}>→</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {!route && !plannerExpanded && !isOptimizing && (
        <TouchableOpacity
          style={[styles.emptyCard, { bottom: 16 + insets.bottom }]}
          onPress={() => setPlannerExpanded(true)}
        >
          <Text style={styles.emptyTitle}>Set two points to begin</Text>
          <Text style={styles.emptyText}>
            Compare travel time and six simultaneous hazard signals.
          </Text>
        </TouchableOpacity>
      )}

      {error && (
        <View style={[styles.errorCard, { bottom: 16 + insets.bottom }]}>
          <View style={styles.errorIcon}>
            <Text style={styles.errorIconText}>!</Text>
          </View>
          <View style={styles.errorCopy}>
            <Text style={styles.errorTitle}>Route unavailable</Text>
            <Text style={styles.errorMessage} numberOfLines={3}>
              {error}
            </Text>
          </View>
          <TouchableOpacity onPress={retryConnection}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {route && !plannerExpanded && (
        <View style={styles.legend}>
          {["low", "moderate", "high", "critical"].map((level) => (
            <View style={styles.legendItem} key={level}>
              <View
                style={[
                  styles.legendLine,
                  { backgroundColor: getRouteRiskColor(level) },
                ]}
              />
              <Text style={styles.legendText}>{getRouteRiskLabel(level)}</Text>
            </View>
          ))}
        </View>
      )}

      <Modal
        visible={analysisVisible}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={() => setAnalysisVisible(false)}
      >
        {routeResult && (
          <View style={[styles.modalContainer, { paddingTop: insets.top }]}>
            <View style={styles.modalHeader}>
              <TouchableOpacity
                style={styles.modalClose}
                onPress={() => setAnalysisVisible(false)}
              >
                <Text style={styles.modalCloseText}>×</Text>
              </TouchableOpacity>
              <View style={styles.modalHeaderCopy}>
                <Text style={styles.modalEyebrow}>ROUTE EVIDENCE</Text>
                <Text style={styles.modalTitle}>Safety analysis</Text>
              </View>
              <TouchableOpacity style={styles.shareButton} onPress={shareRoute}>
                <Text style={styles.shareText}>Share</Text>
              </TouchableOpacity>
            </View>

            <ScrollView
              showsVerticalScrollIndicator={false}
              contentContainerStyle={[
                styles.modalContent,
                { paddingBottom: 30 + insets.bottom },
              ]}
            >
              <View style={styles.heroCard}>
                <View style={styles.heroTop}>
                  <View>
                    <Text style={styles.heroMethod}>
                      {methodIcon(route.method)} {route.method_label}
                    </Text>
                    <Text style={styles.heroTime}>
                      {formatDuration(route.duration_min)}
                    </Text>
                    <Text style={styles.heroDistance}>
                      {route.distance_km.toFixed(1)} km • {route.segment_count} road segments
                      {" • max " + route.detour_guardrail_pct.toFixed(0) + "% detour"}
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.heroRisk,
                      { backgroundColor: riskTint(route.risk_level) },
                    ]}
                  >
                    <Text
                      style={[
                        styles.heroRiskValue,
                        { color: getRouteRiskColor(route.risk_level) },
                      ]}
                    >
                      {Math.round(route.risk_score * 100)}
                    </Text>
                    <Text
                      style={[
                        styles.heroRiskUnit,
                        { color: getRouteRiskColor(route.risk_level) },
                      ]}
                    >
                      risk / 100
                    </Text>
                  </View>
                </View>
                <Text style={styles.recommendation}>{routeResult.recommendation}</Text>
              </View>

              <Text style={styles.sectionTitle}>Method comparison</Text>
              <Text style={styles.sectionSubtitle}>
                Methods are compared on the same network and hazard state. A same-path
                label means the methods selected one identical road path.
              </Text>
              <View style={styles.comparisonList}>
                {routeResult.comparison.map((item) => {
                  const active = item.method === route.method;
                  return (
                    <View
                      key={item.method}
                      style={[
                        styles.comparisonCard,
                        active && styles.comparisonCardActive,
                      ]}
                    >
                      <View style={styles.comparisonMethod}>
                        <Text style={styles.comparisonIcon}>
                          {methodIcon(item.method)}
                        </Text>
                        <View style={styles.comparisonMethodCopy}>
                          <Text style={styles.comparisonName}>
                            {item.method_label}
                          </Text>
                          <Text style={styles.comparisonMeta}>
                            {formatDuration(item.duration_min)} •{" "}
                            {item.distance_km.toFixed(1)} km
                          </Text>
                        </View>
                      </View>
                      <View style={styles.comparisonNumbers}>
                        <Text
                          style={[
                            styles.comparisonRisk,
                            { color: getRouteRiskColor(item.risk_level) },
                          ]}
                        >
                          {Math.round(item.risk_score * 100)}%
                        </Text>
                        <Text style={styles.comparisonReduction}>
                          {item.method !== "shortest_path" && item.same_as_fastest
                            ? "same road path"
                            : item.method === "shortest_path"
                            ? "reference"
                            : item.risk_reduction_vs_fastest_pct > 0
                            ? "↓ " +
                              item.risk_reduction_vs_fastest_pct.toFixed(1) +
                              "% exposure"
                            : "no reduction"}
                        </Text>
                      </View>
                    </View>
                  );
                })}
              </View>

              <Text style={styles.sectionTitle}>Six-hazard profile</Text>
              <Text style={styles.sectionSubtitle}>
                Route-average signals and their reproducible CRITIC information weights.
              </Text>
              <View style={styles.sectionCard}>
                {Object.entries(route.hazard_summary)
                  .sort((first, second) => second[1] - first[1])
                  .map(([name, score]) => {
                    const weight = routeResult.model.objective_weights[name] || 0;
                    return (
                      <View style={styles.hazardRow} key={name}>
                        <Text style={styles.hazardIcon}>{HAZARD_ICONS[name]}</Text>
                        <View style={styles.hazardBody}>
                          <View style={styles.hazardHeader}>
                            <Text style={styles.hazardName}>
                              {HAZARD_LABELS[name]}
                            </Text>
                            <Text style={styles.hazardValue}>
                              {Math.round(score * 100)}%
                            </Text>
                          </View>
                          <View style={styles.hazardTrack}>
                            <View
                              style={[
                                styles.hazardFill,
                                {
                                  width:
                                    Math.max(2, Math.round(score * 100)) + "%",
                                  backgroundColor:
                                    score >= 0.7
                                      ? COLORS.danger
                                      : score >= 0.4
                                      ? "#F59E0B"
                                      : COLORS.primary,
                                },
                              ]}
                            />
                          </View>
                          <Text style={styles.weightLabel}>
                            Objective weight {(weight * 100).toFixed(1)}%
                          </Text>
                        </View>
                      </View>
                    );
                  })}
              </View>

              <Text style={styles.sectionTitle}>Highest-risk road sections</Text>
              <View style={styles.sectionCard}>
                {severeSegments.map((segment, index) => (
                  <View
                    style={[
                      styles.segmentRow,
                      index < severeSegments.length - 1 && styles.rowBorder,
                    ]}
                    key={segment.sequence}
                  >
                    <View
                      style={[
                        styles.segmentNumber,
                        { backgroundColor: riskTint(segment.risk_level) },
                      ]}
                    >
                      <Text
                        style={[
                          styles.segmentNumberText,
                          { color: getRouteRiskColor(segment.risk_level) },
                        ]}
                      >
                        {index + 1}
                      </Text>
                    </View>
                    <View style={styles.segmentCopy}>
                      <Text style={styles.segmentName} numberOfLines={1}>
                        {segment.road_name}
                      </Text>
                      <Text style={styles.segmentMeta}>
                        {segment.distance_km.toFixed(2)} km •{" "}
                        {Math.max(1, Math.round(segment.duration_min))} min
                      </Text>
                    </View>
                    <Text
                      style={[
                        styles.segmentRisk,
                        { color: getRouteRiskColor(segment.risk_level) },
                      ]}
                    >
                      {Math.round(segment.risk_score * 100)}%
                    </Text>
                  </View>
                ))}
              </View>

              <Text style={styles.sectionTitle}>Evidence quality</Text>
              <View style={styles.sectionCard}>
                <View style={styles.qualityHeader}>
                  <View
                    style={[
                      styles.qualityBadge,
                      {
                        backgroundColor: qualityTint(routeResult.data_quality.level)
                          .background,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.qualityBadgeText,
                        {
                          color: qualityTint(routeResult.data_quality.level).text,
                        },
                      ]}
                    >
                      {routeResult.data_quality.level.toUpperCase()} COVERAGE
                    </Text>
                  </View>
                  <Text style={styles.qualityPercent}>
                    {routeResult.data_quality.route_coverage_pct.toFixed(0)}%
                  </Text>
                </View>
                <Text style={styles.qualityMessage}>
                  {routeResult.data_quality.message}
                </Text>
                {routeResult.data_quality.limitations.map((limitation) => (
                  <View style={styles.noteRow} key={limitation}>
                    <Text style={styles.noteBullet}>•</Text>
                    <Text style={styles.noteText}>{limitation}</Text>
                  </View>
                ))}
              </View>

              <Text style={styles.sectionTitle}>Why this decision is auditable</Text>
              <View style={styles.researchCard}>
                <View style={styles.researchRow}>
                  <Text style={styles.researchIcon}>◈</Text>
                  <View style={styles.researchCopy}>
                    <Text style={styles.researchTitle}>No human survey dependency</Text>
                    <Text style={styles.researchText}>
                      Weights are calculated by CRITIC from{" "}
                      {routeResult.model.dataset_rows} hazard observations.
                    </Text>
                  </View>
                </View>
                <View style={styles.researchRow}>
                  <Text style={styles.researchIcon}>↗</Text>
                  <View style={styles.researchCopy}>
                    <Text style={styles.researchTitle}>Monotonic by design</Text>
                    <Text style={styles.researchText}>
                      Increasing any hazard cannot make a road appear safer.
                    </Text>
                  </View>
                </View>
                <View style={styles.researchRow}>
                  <Text style={styles.researchIcon}>≤</Text>
                  <View style={styles.researchCopy}>
                    <Text style={styles.researchTitle}>Detour guardrail</Text>
                    <Text style={styles.researchText}>
                      The route is constrained to at most{" "}
                      {route.detour_guardrail_pct.toFixed(0)}% extra travel time.
                      {route.guardrail_applied
                        ? " The requested preference was automatically adjusted."
                        : " No adjustment was needed."}
                    </Text>
                  </View>
                </View>
                <View style={styles.researchRow}>
                  <Text style={styles.researchIcon}>◎</Text>
                  <View style={styles.researchCopy}>
                    <Text style={styles.researchTitle}>Traceable live state</Text>
                    <Text style={styles.researchText}>
                      Hazard data version {routeResult.network.hazard_version} •{" "}
                      {routeResult.processing_time_ms.toFixed(0)} ms API processing
                    </Text>
                  </View>
                </View>
              </View>

              <Text style={styles.disclaimer}>
                Decision-support prototype only. Risk estimates reduce uncertainty;
                they cannot guarantee that a road is safe or passable.
              </Text>
            </ScrollView>
          </View>
        )}
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#E0F2FE" },
  map: { flex: 1 },
  placeholder: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 32,
    backgroundColor: "#F0F9FF",
  },
  placeholderIcon: { fontSize: 56, marginBottom: 12 },
  placeholderTitle: { fontSize: 22, fontWeight: "800", color: COLORS.navy },
  placeholderText: {
    marginTop: 8,
    fontSize: 14,
    color: COLORS.muted,
    textAlign: "center",
  },
  mapLoading: {
    position: "absolute",
    top: 14,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 13,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.96)",
    elevation: 4,
  },
  mapLoadingText: { fontSize: 11, fontWeight: "700", color: COLORS.slate },

  plannerCard: {
    position: "absolute",
    top: 12,
    left: 12,
    right: 12,
    padding: 14,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.98)",
    elevation: 10,
    shadowColor: "#0F172A",
    shadowOpacity: 0.18,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 7 },
  },
  plannerHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 11,
  },
  titleWrap: { flex: 1, marginRight: 8 },
  eyebrow: {
    fontSize: 8,
    fontWeight: "800",
    color: COLORS.primary,
    letterSpacing: 1,
  },
  title: { marginTop: 2, fontSize: 18, fontWeight: "900", color: COLORS.navy },
  statusPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
  },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  statusOnline: { backgroundColor: "#22C55E" },
  statusChecking: { backgroundColor: "#F59E0B" },
  statusOffline: { backgroundColor: "#EF4444" },
  statusText: { fontSize: 9, fontWeight: "700", color: COLORS.slate },

  locationBlock: { position: "relative", marginBottom: 10 },
  locationRow: {
    minHeight: 48,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 11,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 13,
    backgroundColor: "#F8FAFC",
  },
  locationRowActive: { borderColor: COLORS.primary, backgroundColor: COLORS.softBlue },
  locationDot: { width: 9, height: 9, borderRadius: 5 },
  originDot: { backgroundColor: COLORS.success },
  destinationDot: { backgroundColor: COLORS.danger },
  locationConnector: {
    width: 1,
    height: 6,
    marginLeft: 15,
    backgroundColor: "#CBD5E1",
  },
  locationInputWrap: { flex: 1, marginLeft: 10 },
  locationLabel: {
    fontSize: 8,
    fontWeight: "900",
    color: COLORS.muted,
    letterSpacing: 0.8,
  },
  locationInput: {
    paddingVertical: 1,
    fontSize: 12,
    fontWeight: "700",
    color: COLORS.navy,
  },
  iconButton: {
    width: 31,
    height: 31,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 10,
    backgroundColor: "#E0F2FE",
  },
  iconButtonText: { fontSize: 19, fontWeight: "800", color: COLORS.primaryDark },
  pinButtonText: { fontSize: 18, fontWeight: "800", color: COLORS.primaryDark },
  swapButton: {
    position: "absolute",
    right: 46,
    top: 45,
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    borderWidth: 2,
    borderColor: "#FFFFFF",
    backgroundColor: COLORS.navy,
    elevation: 2,
  },
  swapText: { fontSize: 14, fontWeight: "900", color: "#FFFFFF" },

  locationResults: {
    marginTop: -3,
    marginBottom: 9,
    paddingHorizontal: 10,
    paddingTop: 8,
    paddingBottom: 5,
    borderWidth: 1,
    borderColor: "#BAE6FD",
    borderRadius: 13,
    backgroundColor: "#FFFFFF",
  },
  locationResultsHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingBottom: 5,
  },
  locationResultsTitle: { fontSize: 9, fontWeight: "800", color: COLORS.muted },
  locationResultsClose: { fontSize: 9, fontWeight: "800", color: COLORS.primaryDark },
  locationResultRow: {
    minHeight: 39,
    flexDirection: "row",
    alignItems: "center",
    borderTopWidth: 1,
    borderTopColor: "#F1F5F9",
  },
  locationResultIcon: {
    width: 24,
    fontSize: 11,
    fontWeight: "900",
    color: COLORS.primary,
    textAlign: "center",
  },
  locationResultCopy: { flex: 1, paddingVertical: 5 },
  locationResultName: { fontSize: 11, fontWeight: "800", color: COLORS.navy },
  locationResultMeta: { marginTop: 1, fontSize: 8, color: COLORS.muted },
  locationEmpty: {
    paddingVertical: 8,
    fontSize: 9,
    lineHeight: 13,
    color: COLORS.muted,
    textAlign: "center",
  },

  methodRow: { flexDirection: "row", gap: 6, marginBottom: 9 },
  methodChip: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
  },
  methodChipActive: { borderColor: "#7DD3FC", backgroundColor: COLORS.softBlue },
  methodIcon: { fontSize: 14 },
  methodName: { marginTop: 2, fontSize: 10, fontWeight: "800", color: COLORS.slate },
  methodNameActive: { color: COLORS.primaryDark },
  methodDetail: { marginTop: 1, fontSize: 7.5, color: "#94A3B8" },
  methodDetailActive: { color: "#0284C7" },

  preferenceRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 9,
  },
  preferenceLabel: { fontSize: 9, fontWeight: "700", color: COLORS.muted },
  preferenceChips: {
    flexDirection: "row",
    padding: 2,
    borderRadius: 9,
    backgroundColor: "#F1F5F9",
  },
  preferenceChip: { paddingHorizontal: 8, paddingVertical: 5, borderRadius: 7 },
  preferenceChipActive: { backgroundColor: "#FFFFFF", elevation: 1 },
  preferenceText: { fontSize: 8, fontWeight: "700", color: "#94A3B8" },
  preferenceTextActive: { color: COLORS.primaryDark },

  calculateButton: {
    minHeight: 43,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 13,
    backgroundColor: COLORS.primary,
    shadowColor: COLORS.primary,
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  calculateButtonDisabled: { opacity: 0.75 },
  calculateIcon: { fontSize: 14, color: "#FFFFFF" },
  calculateText: { fontSize: 13, fontWeight: "900", color: "#FFFFFF" },
  selectionHint: {
    marginTop: 7,
    fontSize: 9,
    fontWeight: "700",
    color: COLORS.primaryDark,
    textAlign: "center",
  },

  compactPlanner: {
    position: "absolute",
    top: 12,
    left: 12,
    right: 12,
    minHeight: 56,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    borderRadius: 18,
    backgroundColor: "rgba(255,255,255,0.98)",
    elevation: 8,
    shadowColor: "#0F172A",
    shadowOpacity: 0.15,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
  },
  compactRouteLine: { flex: 1, flexDirection: "row", alignItems: "center", gap: 7 },
  compactLocation: {
    maxWidth: "31%",
    fontSize: 10,
    fontWeight: "700",
    color: COLORS.navy,
  },
  compactArrow: { fontSize: 13, color: COLORS.muted },
  compactEdit: {
    marginLeft: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 10,
    backgroundColor: COLORS.softBlue,
  },
  compactEditText: { fontSize: 10, fontWeight: "800", color: COLORS.primaryDark },

  markerHalo: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 19,
  },
  markerCore: {
    width: 25,
    height: 25,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    borderWidth: 2,
    borderColor: "#FFFFFF",
    elevation: 3,
  },
  markerText: { fontSize: 10, fontWeight: "900", color: "#FFFFFF" },

  summaryCard: {
    position: "absolute",
    left: 12,
    right: 12,
    paddingHorizontal: 15,
    paddingBottom: 14,
    borderRadius: 22,
    backgroundColor: "rgba(255,255,255,0.98)",
    elevation: 10,
    shadowColor: "#0F172A",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 7 },
  },
  summaryHandle: {
    width: 34,
    height: 4,
    alignSelf: "center",
    marginTop: 7,
    marginBottom: 9,
    borderRadius: 2,
    backgroundColor: "#CBD5E1",
  },
  summaryHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  summaryTitleWrap: { flex: 1, marginRight: 12 },
  summaryKicker: { fontSize: 9, fontWeight: "800", color: COLORS.primaryDark },
  summaryTitle: { marginTop: 3, fontSize: 22, fontWeight: "900", color: COLORS.navy },
  summaryTitleMuted: { fontSize: 13, fontWeight: "700", color: COLORS.muted },
  riskBadge: {
    minWidth: 71,
    alignItems: "center",
    paddingHorizontal: 9,
    paddingVertical: 7,
    borderRadius: 13,
  },
  riskBadgeValue: { fontSize: 16, fontWeight: "900" },
  riskBadgeLabel: { marginTop: 1, fontSize: 8, fontWeight: "800" },
  sameRouteNotice: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 11,
    backgroundColor: "#EFF6FF",
  },
  sameRouteIcon: {
    width: 25,
    height: 25,
    borderRadius: 13,
    backgroundColor: "#DBEAFE",
    color: COLORS.primaryDark,
    fontSize: 13,
    fontWeight: "900",
    textAlign: "center",
    textAlignVertical: "center",
  },
  sameRouteCopy: { flex: 1, marginLeft: 8 },
  sameRouteTitle: { fontSize: 9.5, fontWeight: "900", color: COLORS.primaryDark },
  sameRouteText: { marginTop: 1, fontSize: 7.5, lineHeight: 11, color: COLORS.slate },
  liveRefreshNotice: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 7,
    borderRadius: 10,
    backgroundColor: "#ECFDF5",
  },
  liveRefreshDot: {
    width: 7,
    height: 7,
    marginRight: 7,
    borderRadius: 4,
    backgroundColor: COLORS.success,
  },
  liveRefreshText: { fontSize: 8.5, fontWeight: "800", color: "#166534" },
  insightStrip: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 12,
    paddingVertical: 9,
    borderRadius: 12,
    backgroundColor: "#F8FAFC",
  },
  insightItem: { flex: 1, alignItems: "center" },
  insightValue: { fontSize: 11, fontWeight: "900", color: COLORS.navy },
  insightLabel: { marginTop: 2, fontSize: 7.5, color: COLORS.muted },
  insightDivider: { width: 1, height: 27, backgroundColor: COLORS.line },
  topHazards: { gap: 6, paddingVertical: 9 },
  hazardPill: {
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 9,
    backgroundColor: COLORS.softBlue,
  },
  hazardPillText: { fontSize: 8.5, fontWeight: "700", color: COLORS.primaryDark },
  summaryActions: { flexDirection: "row", gap: 8 },
  secondaryButton: {
    minHeight: 39,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 12,
  },
  secondaryButtonText: { fontSize: 10, fontWeight: "800", color: COLORS.slate },
  analysisButton: {
    flex: 1,
    minHeight: 39,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: 12,
    backgroundColor: COLORS.primary,
  },
  analysisButtonText: { fontSize: 11, fontWeight: "900", color: "#FFFFFF" },
  analysisButtonArrow: { fontSize: 13, fontWeight: "900", color: "#FFFFFF" },

  legend: {
    position: "absolute",
    top: 79,
    right: 12,
    gap: 5,
    padding: 9,
    borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.94)",
    elevation: 4,
  },
  legendItem: { flexDirection: "row", alignItems: "center", gap: 6 },
  legendLine: { width: 17, height: 4, borderRadius: 2 },
  legendText: { fontSize: 8, fontWeight: "600", color: COLORS.slate },

  errorCard: {
    position: "absolute",
    left: 12,
    right: 12,
    flexDirection: "row",
    alignItems: "center",
    padding: 13,
    borderWidth: 1,
    borderColor: "#FECACA",
    borderRadius: 16,
    backgroundColor: "#FEF2F2",
    elevation: 8,
  },
  errorIcon: {
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 14,
    backgroundColor: "#FEE2E2",
  },
  errorIconText: { fontSize: 14, fontWeight: "900", color: COLORS.danger },
  errorCopy: { flex: 1, marginHorizontal: 10 },
  errorTitle: { fontSize: 11, fontWeight: "900", color: "#991B1B" },
  errorMessage: { marginTop: 2, fontSize: 9, lineHeight: 13, color: "#B91C1C" },
  retryText: { fontSize: 10, fontWeight: "900", color: COLORS.primaryDark },
  emptyCard: {
    position: "absolute",
    left: 12,
    right: 12,
    alignItems: "center",
    padding: 15,
    borderRadius: 16,
    backgroundColor: "rgba(255,255,255,0.96)",
    elevation: 5,
  },
  emptyTitle: { fontSize: 12, fontWeight: "900", color: COLORS.navy },
  emptyText: { marginTop: 3, fontSize: 9, color: COLORS.muted },

  modalContainer: { flex: 1, backgroundColor: "#F8FAFC" },
  modalHeader: {
    minHeight: 65,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.line,
    backgroundColor: "#FFFFFF",
  },
  modalClose: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 17,
    backgroundColor: "#F1F5F9",
  },
  modalCloseText: { marginTop: -2, fontSize: 24, color: COLORS.slate },
  modalHeaderCopy: { flex: 1, marginLeft: 11 },
  modalEyebrow: {
    fontSize: 8,
    fontWeight: "900",
    letterSpacing: 1,
    color: COLORS.primary,
  },
  modalTitle: { fontSize: 18, fontWeight: "900", color: COLORS.navy },
  shareButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: COLORS.softBlue,
  },
  shareText: { fontSize: 10, fontWeight: "900", color: COLORS.primaryDark },
  modalContent: { padding: 16 },
  heroCard: {
    padding: 16,
    borderRadius: 18,
    backgroundColor: COLORS.navy,
  },
  heroTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  heroMethod: { fontSize: 10, fontWeight: "800", color: "#7DD3FC" },
  heroTime: { marginTop: 4, fontSize: 31, fontWeight: "900", color: "#FFFFFF" },
  heroDistance: { marginTop: 2, fontSize: 9, color: "#CBD5E1" },
  heroRisk: {
    minWidth: 76,
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 9,
    borderRadius: 15,
  },
  heroRiskValue: { fontSize: 24, fontWeight: "900" },
  heroRiskUnit: { fontSize: 8, fontWeight: "800" },
  recommendation: {
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#334155",
    fontSize: 10,
    lineHeight: 15,
    color: "#E2E8F0",
  },
  sectionTitle: {
    marginTop: 22,
    fontSize: 15,
    fontWeight: "900",
    color: COLORS.navy,
  },
  sectionSubtitle: {
    marginTop: 3,
    marginBottom: 10,
    fontSize: 9,
    lineHeight: 13,
    color: COLORS.muted,
  },
  comparisonList: { gap: 8 },
  comparisonCard: {
    minHeight: 67,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
  },
  comparisonCardActive: { borderColor: "#7DD3FC", backgroundColor: COLORS.softBlue },
  comparisonMethod: { flex: 1, flexDirection: "row", alignItems: "center" },
  comparisonIcon: { fontSize: 18, marginRight: 9 },
  comparisonMethodCopy: { flex: 1 },
  comparisonName: { fontSize: 10, fontWeight: "900", color: COLORS.navy },
  comparisonMeta: { marginTop: 3, fontSize: 8.5, color: COLORS.muted },
  comparisonNumbers: { alignItems: "flex-end", marginLeft: 8 },
  comparisonRisk: { fontSize: 14, fontWeight: "900" },
  comparisonReduction: { marginTop: 2, fontSize: 7.5, color: COLORS.muted },
  sectionCard: {
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: COLORS.line,
    borderRadius: 16,
    backgroundColor: "#FFFFFF",
  },
  hazardRow: { flexDirection: "row", paddingVertical: 12 },
  hazardIcon: { width: 28, fontSize: 18 },
  hazardBody: { flex: 1 },
  hazardHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  hazardName: { fontSize: 10, fontWeight: "800", color: COLORS.navy },
  hazardValue: { fontSize: 10, fontWeight: "900", color: COLORS.slate },
  hazardTrack: {
    height: 5,
    marginTop: 6,
    overflow: "hidden",
    borderRadius: 3,
    backgroundColor: "#E2E8F0",
  },
  hazardFill: { height: 5, borderRadius: 3 },
  weightLabel: { marginTop: 4, fontSize: 7.5, color: "#94A3B8" },
  segmentRow: { flexDirection: "row", alignItems: "center", paddingVertical: 11 },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: "#F1F5F9" },
  segmentNumber: {
    width: 28,
    height: 28,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 9,
  },
  segmentNumberText: { fontSize: 10, fontWeight: "900" },
  segmentCopy: { flex: 1, marginHorizontal: 10 },
  segmentName: { fontSize: 10, fontWeight: "800", color: COLORS.navy },
  segmentMeta: { marginTop: 3, fontSize: 8, color: COLORS.muted },
  segmentRisk: { fontSize: 11, fontWeight: "900" },
  qualityHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: 14,
  },
  qualityBadge: { paddingHorizontal: 9, paddingVertical: 5, borderRadius: 8 },
  qualityBadgeText: { fontSize: 8, fontWeight: "900" },
  qualityPercent: { fontSize: 18, fontWeight: "900", color: COLORS.navy },
  qualityMessage: {
    marginTop: 9,
    marginBottom: 8,
    fontSize: 10,
    lineHeight: 15,
    color: COLORS.slate,
  },
  noteRow: { flexDirection: "row", paddingBottom: 8 },
  noteBullet: { width: 14, fontSize: 11, color: COLORS.primary },
  noteText: { flex: 1, fontSize: 8.5, lineHeight: 13, color: COLORS.muted },
  researchCard: {
    marginTop: 10,
    padding: 14,
    borderRadius: 16,
    backgroundColor: "#E0F2FE",
  },
  researchRow: { flexDirection: "row", marginBottom: 13 },
  researchIcon: {
    width: 30,
    fontSize: 18,
    fontWeight: "900",
    color: COLORS.primaryDark,
  },
  researchCopy: { flex: 1 },
  researchTitle: { fontSize: 10, fontWeight: "900", color: COLORS.primaryDark },
  researchText: {
    marginTop: 3,
    fontSize: 8.5,
    lineHeight: 13,
    color: COLORS.slate,
  },
  disclaimer: {
    marginTop: 18,
    fontSize: 8,
    lineHeight: 12,
    textAlign: "center",
    color: "#94A3B8",
  },
});
