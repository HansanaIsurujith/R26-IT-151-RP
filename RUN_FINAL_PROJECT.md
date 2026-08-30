# Suraksha Lanka — Run the Final Integrated Project

This ZIP contains the original Flood/Landslide work plus the completed,
separate Route Optimization component. No Flood/Landslide model, endpoint,
dataset or map logic was removed.

## 1. Requirements

- Python 3.11 or newer (Python 3.14 is supported)
- Node.js 20.19.4 or newer
- Android/iOS phone with Expo Go, or an emulator
- Phone and computer connected to the same Wi-Fi network

The interactive map is intended for Android/iOS. The existing project shows a
map-unavailable placeholder on web.

## 2. Start the Route Optimization API

Open a terminal in the project root:

### Windows

~~~powershell
cd backend\Route-Optimization
py -3.14 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python run_api.py
~~~

### macOS/Linux

~~~bash
cd backend/Route-Optimization
python3 -m pip install -r requirements.txt
python3 run_api.py
~~~

The server binds to 0.0.0.0:8001. Open http://127.0.0.1:8001 on the PC;
0.0.0.0 is not a browser destination. The real Gampaha road graph has
73,603 nodes and 165,094 edges, so initial startup can take roughly 20–30
seconds while the graph and fuzzy-risk cache are prepared. Wait for:

~~~text
Application startup complete
~~~

Then check http://127.0.0.1:8001/health or open
http://127.0.0.1:8001/docs.

## 3. Configure the Mobile App

Find the computer's Wi-Fi IPv4 address:

~~~powershell
ipconfig
~~~

In suraksha-lanka, copy .env.example to .env and replace
YOUR_PC_IP. Example:

~~~env
EXPO_PUBLIC_ROUTE_API_URL=http://192.168.1.25:8001
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=YOUR_RESTRICTED_ANDROID_MAPS_KEY
~~~

Do not use localhost for a physical phone; on the phone, localhost means the
phone itself. The route client can infer Expo's LAN host when .env is absent,
but the explicit value is recommended for a predictable presentation.

The repository contains no hard-coded Maps credential. Expo Go can use its
built-in map configuration; a standalone Android build requires your own
Google Maps key, restricted in Google Cloud.

## 4. Start React Native / Expo

Open a second terminal:

~~~powershell
cd suraksha-lanka
npm install
set REACT_NATIVE_PACKAGER_HOSTNAME=YOUR_PC_IP
npx expo start --lan -c
~~~

Scan the QR code with Expo Go. If Windows Firewall asks, allow Node.js and
Python on private networks.

## 5. Test the Completed Route Flow

1. Open **Risk-Aware Route Optimization** on the home screen.
2. Search for **Gampaha** and **Nittambuwa** by name and select the suggestions.
3. Select **Risk Aware**, choose a risk preference and press **Find best route**.
4. Confirm the coloured route, start/end pins, travel time, distance, risk
   percentage, severe sections, hazard chips and comparison message.
5. Open **View full analysis** and confirm the three-method comparison,
   six-hazard profile, objective weights, evidence quality and road sections.
6. Search another town/road name or tap the displayed Gampaha map; map taps are
   reverse-labelled with a nearby place or road name.
7. Switch to **Objective** and **Fastest** to compare both baselines.
8. If Risk-Aware and Fastest select one identical path, confirm the explicit
   **Same road path as Fastest** message. This is a valid result, not a UI bug.

The graph intentionally covers Gampaha District only. Selecting a current GPS
position far outside Gampaha returns a clear coverage message; that is not a
connection failure.

## 6. Run Verification Checks

Backend:

~~~powershell
cd backend\Route-Optimization
py -m pytest
~~~

Frontend:

~~~powershell
cd suraksha-lanka
npm run typecheck
~~~

Production bundle smoke test:

~~~powershell
cd suraksha-lanka
npx expo export --platform android --output-dir dist-test
~~~

The automated checks cannot press controls on your physical phone. Complete
and record every row in `PHONE_ACCEPTANCE_TEST.md` before saying that phone
runtime is validated.

## 7. Demonstrate a Live Hazard Update

With a route open in the app, post an update using the PowerShell command in
`PHONE_ACCEPTANCE_TEST.md`. The app checks the hazard version every eight
seconds, recalculates the open route and displays the updated version. Updates
are stored in SQLite and replayed after restart.

For reproducible backend evidence without changing the persistent live state:

~~~powershell
cd backend\Route-Optimization
python scripts\demonstrate_live_hazard_update.py
~~~

This script labels the event as simulated. A teammate's actual detector must
use the same `/hazards/update` contract before you describe it as a deployed
team integration.

To connect the included Flood/Landslide service automatically, keep ports 8000
and 8001 running and open a third terminal:

~~~powershell
cd backend\Route-Optimization
python scripts\sync_flood_landslide_service.py --once
~~~

Remove `--once` to poll every five minutes. The bridge forwards the highest-risk
source grid cells, preserves their probabilities, and identifies every update
as `flood_landslide_api_bridge`.

## Whole-Team Application

The existing Flood/Landslide service still runs independently on port 8000.
Run it as your teammate previously documented when testing the Flood and
Landslide Map screen. The completed Route Optimization service uses port 8001,
so both services can run together without endpoint or file conflicts.
