# Suraksha Lanka  R26-IT-151

## AI-Powered Smart Disaster Management and Intelligent Transportation System for Sri Lanka

---

# Project Overview

Suraksha Lanka is an AI-powered smart safety and transportation platform designed specifically for Sri Lankan environmental and road conditions. The system integrates disaster prediction, intelligent transportation analysis, real-time monitoring, and machine learning technologies to improve public safety, reduce transportation risks, and support smarter decision-making.

The platform combines four major intelligent components into one unified system:

1. AI-based Flood Prediction and Risk Assessment
2. Wildlife Movement and Slippery Area Detection
3. AI-based Fuel Prediction and Route Optimization
4. Smart Route Optimization System

The main goal of Suraksha Lanka is to provide real-time insights, early warnings, and optimized travel solutions using AI, machine learning, environmental data, and map-based technologies.

---

# Objectives

* Predict flood-prone areas using environmental and weather data
* Detect risky wildlife movement and slippery road locations
* Predict fuel consumption for selected routes using AI models
* Recommend optimized and safer travel routes
* Provide real-time map visualization and alerts
* Improve transportation safety and disaster preparedness in Sri Lanka

---

# System Architecture

The system consists of:

* Frontend Mobile/Web Application
* Backend API Services
* Machine Learning Prediction Models
* Real-time Data Collection Services
* Database Management System
* Map and Visualization Services

The frontend communicates with backend APIs to retrieve prediction results, alerts, route recommendations, and map visualizations.

Machine learning models process environmental and transportation-related data to generate intelligent predictions.

---

# Technologies Used

## Frontend

* React Native
* Next.js
* Tailwind CSS
* TypeScript
* React Native Maps

## Backend

* FastAPI
* Node.js
* Express.js

## Database

* PostgreSQL
* MongoDB
* Supabase

## Machine Learning

* Python
* Scikit-learn
* XGBoost
* Random Forest
* Pandas
* NumPy

## APIs & Data Sources

* NASA POWER API
* OpenWeather API
* OpenStreetMap API
* Open-Elevation API
* Department of Meteorology Sri Lanka

---

# Component 1 — AI-based Flood Prediction and Risk Assessment

## Problem Statement

Sri Lanka frequently experiences floods due to heavy rainfall, poor drainage systems, low-lying terrain, and extreme weather conditions. Existing systems often fail to provide localized and real-time flood warnings.

---

## Solution

This component predicts flood risks using:

* Rainfall data
* Temperature
* Humidity
* Elevation
* Historical weather patterns
* Geographic location data

The system analyzes environmental conditions and predicts flood risks for different regions.

---

## Features

* Real-time flood prediction
* Flood risk classification
* Risk map visualization
* Early warning alerts
* Environmental data analysis
* AI-powered prediction engine

---

## Machine Learning Workflow

### Step 1

Collect environmental and weather data from APIs.

### Step 2

Preprocess datasets and generate features.

### Step 3

Train machine learning classification models.

### Step 4

Predict flood risk levels.

### Step 5

Display alerts and map visualizations.

---

## Dataset Features

| Feature     | Description               |
| ----------- | ------------------------- |
| rainfall    | Daily rainfall            |
| rain_3d     | Rainfall over last 3 days |
| rain_7d     | Rainfall over last 7 days |
| temperature | Daily temperature         |
| humidity    | Humidity percentage       |
| elevation   | Area elevation            |
| latitude    | Latitude coordinate       |
| longitude   | Longitude coordinate      |
| event       | Flood risk classification |

---

## Recommended Models

* Random Forest Classifier
* XGBoost Classifier
* Gradient Boosting

---

# Component 2 — Wildlife Movement and Slippery Area Detection

## Problem Statement

Road accidents in Sri Lanka frequently occur due to wildlife crossings and slippery road conditions during rainy weather.

Drivers often do not receive early warnings about dangerous road sections.

---

## Solution

This component detects:

* Wildlife movement areas
* Slippery road conditions
* High-risk travel zones

The system provides map-based warnings and safety alerts to drivers.

---

## Features

* Wildlife crossing detection
* Slippery area identification
* Real-time road safety alerts
* Risk visualization on maps
* Driver safety notifications

---

## Data Sources

* Weather conditions
* Rainfall data
* Road condition information
* Historical accident records
* Wildlife movement zones

---

## System Workflow

### Step 1

Collect environmental and road condition data.

### Step 2

Analyze road risk conditions.

### Step 3

Identify dangerous areas.

### Step 4

Display warnings on map.

### Step 5

Notify users in real-time.

---

# Component 3 — AI-based Fuel Prediction and Route Optimization

## Problem Statement

Current navigation systems mainly optimize routes based on shortest distance or travel time.

They do not accurately predict fuel consumption based on:

* Traffic conditions
* Elevation
* Road conditions
* Weather conditions
* Vehicle type

This creates unnecessary fuel costs for drivers and logistics companies.

---

## Solution

This component uses machine learning models to predict fuel consumption for selected routes.

The system analyzes:

* Traffic density
* Route elevation
* Vehicle type
* Road conditions
* Weather conditions
* Average speed

It then recommends fuel-efficient routes.

---

## Features

* AI fuel prediction
* Fuel-efficient route suggestions
* Fuel cost estimation
* Eco-friendly route recommendations
* Carbon emission estimation
* Real-time route analytics

---

## Machine Learning Workflow

### Step 1

User selects a route.

### Step 2

Map APIs calculate route features.

### Step 3

Backend sends route data to ML model.

### Step 4

ML model predicts fuel consumption.

### Step 5

Frontend displays predictions and optimized routes.

---

## Dataset Features

| Feature           | Description             |
| ----------------- | ----------------------- |
| distance_km       | Route distance          |
| avg_speed         | Average speed           |
| traffic_level     | Traffic density         |
| road_type         | Highway / City / Rural  |
| elevation_gain    | Terrain elevation       |
| vehicle_type      | Vehicle category        |
| weather_condition | Weather condition       |
| fuel_used         | Actual fuel consumption |

---

## Recommended Models

* XGBoost Regressor
* Random Forest Regressor
* Gradient Boosting Regressor

---

# Component 4 — Smart Route Optimization System

## Problem Statement

Drivers in Sri Lanka face issues such as:

* Heavy traffic congestion
* Unsafe roads
* Flood-prone routes
* Slippery areas
* High fuel consumption

Existing map applications do not combine all these risk factors together.

---

## Solution

The Smart Route Optimization System calculates safer and more efficient routes by combining:

* Traffic conditions
* Flood risks
* Slippery areas
* Wildlife movement risks
* Fuel optimization

The system dynamically recommends the best route.

---

## Features

* Smart route recommendations
* Safety-aware navigation
* Traffic-aware routing
* Flood avoidance routing
* Fuel-efficient routing
* Real-time map visualization

---

## Workflow

### Step 1

User selects source and destination.

### Step 2

System retrieves map and traffic data.

### Step 3

Risk analysis engine evaluates route conditions.

### Step 4

Optimization engine selects best route.

### Step 5

Frontend displays safest and most efficient routes.

---

# How the Entire System Works

## Step 1 — Data Collection

The system collects real-time and historical data from:

* Weather APIs
* Environmental APIs
* Map services
* Elevation services
* Transportation data sources

---

## Step 2 — Data Processing

The backend preprocesses:

* Weather data
* Flood data
* Traffic data
* Route information
* Elevation information

The processed data is prepared for machine learning models.

---

## Step 3 — Machine Learning Predictions

AI models analyze incoming data and generate:

* Flood risk predictions
* Fuel usage predictions
* Risk assessments
* Smart route recommendations

---

## Step 4 — Backend API Services

Backend services expose prediction results through APIs.

Frontend applications request:

* Flood alerts
* Route recommendations
* Fuel estimations
* Safety notifications

---

## Step 5 — Frontend Visualization

Users interact with:

* Interactive maps
* Real-time alerts
* Route recommendations
* Risk visualizations
* Fuel analytics dashboards

---

# Commercialization and Sustainability

Suraksha Lanka can be commercialized as a smart disaster management and intelligent transportation platform.

Potential customers include:

* Government agencies
* Logistics companies
* Transportation services
* Insurance companies
* Smart city initiatives
* Tourism sector

Revenue can be generated through:

* Subscription services
* Enterprise partnerships
* API access plans
* Premium application features

---

# Unique Features of the Solution

* Combines four AI-powered components into one unified platform
* Designed specifically for Sri Lankan road and environmental conditions
* Provides real-time prediction and visualization
* Uses machine learning for intelligent decision-making
* Supports safer and smarter transportation
* Integrates environmental and transportation intelligence together

---

# Future Improvements

* Real-time IoT sensor integration
* Drone-based environmental monitoring
* Advanced deep learning models
* EV battery optimization support
* Voice-assisted navigation
* Nationwide smart city integration

---

# Validation Targets

| Metric                     | Target      |
| -------------------------- | ----------- |
| Flood prediction accuracy  | >= 90%      |
| Fuel prediction accuracy   | >= 90%      |
| API response latency       | < 2 seconds |
| Route recalculation time   | < 5 seconds |
| Concurrent users supported | 500+        |

---

# Conclusion

Suraksha Lanka is an intelligent AI-powered platform that combines disaster management, transportation safety, route optimization, and environmental intelligence into one scalable solution.

The project aims to improve road safety, disaster preparedness, fuel efficiency, and transportation decision-making in Sri Lanka using modern AI and real-time technologies.

---

# Team Components Summary

| Component   | Description                                     |
| ----------- | ----------------------------------------------- |
| Component 1 | AI-based Flood Prediction and Risk Assessment   |
| Component 2 | Wildlife Movement and Slippery Area Detection   |
| Component 3 | AI-based Fuel Prediction and Route Optimization |
| Component 4 | Smart Route Optimization System                 |

---

# Project Name

## Suraksha Lanka

Smart AI-powered Disaster Management and Intelligent Transportation Platform for Sri Lanka.
