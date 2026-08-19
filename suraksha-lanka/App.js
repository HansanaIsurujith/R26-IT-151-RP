import React from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { View, Text } from "react-native";
import HomeScreen from "./src/screens/HomeScreen";
import MapScreen from "./src/screens/MapScreen";

const Stack = createNativeStackNavigator();

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("App Error:", error);
    console.error("Error Info:", errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <SafeAreaProvider>
          <View
            style={{
              flex: 1,
              justifyContent: "center",
              alignItems: "center",
              backgroundColor: "#f3f4f6",
              padding: 20,
            }}
          >
            <Text
              style={{
                fontSize: 20,
                fontWeight: "bold",
                marginBottom: 15,
                color: "#dc2626",
              }}
            >
              ⚠️ Application Error
            </Text>
            <Text
              style={{
                fontSize: 14,
                color: "#4b5563",
                textAlign: "center",
                marginBottom: 15,
                lineHeight: 20,
              }}
            >
              {this.state.error?.message || "An unexpected error occurred"}
            </Text>
            {this.state.errorInfo && (
              <Text
                style={{
                  fontSize: 11,
                  color: "#9ca3af",
                  textAlign: "center",
                  fontFamily: "monospace",
                }}
              >
                {this.state.errorInfo.componentStack?.substring(0, 200)}
              </Text>
            )}
          </View>
        </SafeAreaProvider>
      );
    }

    return this.props.children;
  }
}

function NavigationStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: true,
        animationEnabled: true,
        headerStyle: {
          backgroundColor: "#0ea5e9",
        },
        headerTintColor: "#fff",
        headerTitleStyle: {
          fontWeight: "700",
          fontSize: 18,
          color: "#fff",
        },
      }}
    >
      <Stack.Screen
        name="Home"
        component={HomeScreen}
        options={{
          title: "Suraksha Lanka",
          headerBackVisible: false,
        }}
      />
      <Stack.Screen
        name="Map"
        component={MapScreen}
        options={{
          title: "Map View",
        }}
      />
    </Stack.Navigator>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <SafeAreaProvider>
        <NavigationContainer>
          <NavigationStack />
        </NavigationContainer>
      </SafeAreaProvider>
    </ErrorBoundary>
  );
}