# Physical Phone Acceptance Test

This is the final manual check that cannot be completed by automated desktop
tests. Record the phone screen and the API terminal together for viva evidence.

## One-time setup

1. Install Node.js 20.19.4 or newer and Expo Go.
2. Put the phone and computer on the same Wi-Fi network.
3. Copy `suraksha-lanka/.env.example` to `suraksha-lanka/.env`.
4. Set `EXPO_PUBLIC_ROUTE_API_URL` to the computer's Wi-Fi IPv4 address, not
   `localhost`, for example `http://192.168.1.25:8001`.
5. Keep the Maps key restricted to the Android application/API in Google Cloud.

## Required acceptance evidence

Start the backend, then Expo, using `RUN_FINAL_PROJECT.md`. Complete every row:

| Check | Expected evidence | Result |
|---|---|---|
| API readiness | Phone shows `Live • data v...`; PC `/health` returns 200 | Pending on physical phone |
| Name search | Typing `Gampaha` and `Nittambuwa` shows selectable names, not coordinates | Pending on physical phone |
| Optimize call | Backend terminal shows `POST /route/optimize 200 OK` | Pending on physical phone |
| Route drawing | Coloured road path, A/B markers, time, distance and proxy risk appear | Pending on physical phone |
| Three methods | Risk-Aware, Objective and Fastest each return a result | Pending on physical phone |
| Same-path case | If identical, UI says `Same road path as Fastest` instead of presenting a false alternative | Pending on physical phone |
| Swap | From/To names and route swap correctly | Pending on physical phone |
| Outside coverage | A point well outside Gampaha gives a clear coverage warning | Pending on physical phone |
| Live update | After `POST /hazards/update`, app refreshes within about 8 seconds and shows the new data version | Pending on physical phone |

## Live-update demonstration

First calculate Gampaha to Nittambuwa in the app. In PowerShell, send an update
near the displayed route:

~~~powershell
$body = @{
  coordinate = @{ latitude = 7.12; longitude = 80.04; label = "Demo detector cell" }
  radius_km = 2.0
  hazards = @{ flood = 1.0; landslide = 1.0 }
  source = "team_flood_detector_demo"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8001/hazards/update" `
  -ContentType "application/json" `
  -Body $body
~~~

Confirm that `hazard_version` increases. The app polls the status endpoint and
recalculates an open route within about eight seconds. A different route is
recommended only when the updated network offers a lower-exposure alternative
inside the detour guardrail; otherwise the same-path explanation is expected.

## Claim to use after the test

“The mobile client successfully called the route-optimization API and rendered
a risk-aware result on the tested phone and local network.”

Do not convert this into a claim of guaranteed road safety or perfect real-world
accuracy.
