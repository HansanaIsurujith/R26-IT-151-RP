"""
Suraksha Lanka — NASA Landslide Data Integration
Project : R26-IT-151
Student : IT22294470

Integrates NASA Global Landslide Catalog with dataset.
Uses 2km buffer around verified landslide events
to mark nearby grid points as landslide = 1.
"""

import pandas as pd
import numpy as np

NASA_CSV   = "dataset/Global_Landslide_Catalog_Export_rows.csv"
MASTER_CSV = "dataset/gampaha_master_dataset.csv"
OUTPUT_CSV = "dataset/gampaha_master_nasa_dataset.csv"

# Gampaha bounds (slightly expanded for buffer)
LAT_MIN, LAT_MAX = 6.90, 7.50
LNG_MIN, LNG_MAX = 79.80, 80.50
BUFFER_KM = 2.0  # 2km buffer around each event

print("=" * 55)
print("  NASA Landslide Integration")
print("=" * 55)

# ── Load NASA Data ─────────────────────────────────────────
nasa = pd.read_csv(NASA_CSV)
lk   = nasa[nasa['country_name'].str.contains('Sri Lanka', na=False)]

# Broader area filter (Western Province + adjacent)
events = lk[
    (lk['latitude']  >= LAT_MIN) & (lk['latitude']  <= LAT_MAX) &
    (lk['longitude'] >= LNG_MIN) & (lk['longitude'] <= LNG_MAX)
].copy()

# Keep only rainfall-triggered
rainfall_triggers = ['rain', 'downpour', 'continuous_rain', 'monsoon', 'tropical_cyclone']
events = events[events['landslide_trigger'].isin(rainfall_triggers)]

print(f"\n  NASA events (Western Province + rainfall): {len(events)}")
print(f"  Events:")
for _, row in events.iterrows():
    print(f"    ({row['latitude']:.3f}, {row['longitude']:.3f}) "
          f"— {row['event_date'][:10]} "
          f"— {row['landslide_category']} "
          f"— {row['landslide_trigger']}")

# ── Load Master Dataset ────────────────────────────────────
print(f"\n  Loading master dataset...")
try:
    df = pd.read_csv(MASTER_CSV)
    print(f"  Rows: {len(df)}")
except FileNotFoundError:
    # If master not built yet, use unosat dataset
    df = pd.read_csv("dataset/gampaha_unosat_dataset.csv")
    print(f"  Using unosat dataset: {len(df)} rows")

# ── Calculate Distance ─────────────────────────────────────
def haversine_km(lat1, lng1, lat2, lng2):
    """Haversine distance in km."""
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlng = np.radians(lng2 - lng1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * \
        np.cos(np.radians(lat2)) * np.sin(dlng/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

# ── Mark Grid Points near NASA Events ─────────────────────
print(f"\n  Marking grid points within {BUFFER_KM}km of NASA events...")

df['nasa_landslide']        = 0
df['nasa_nearest_event_km'] = 999.0
df['nasa_trigger']          = ''

for _, event in events.iterrows():
    elat = event['latitude']
    elng = event['longitude']

    # Calculate distance from each grid point to this event
    dist = df.apply(
        lambda row: haversine_km(row['latitude'], row['longitude'], elat, elng),
        axis=1
    )

    # Mark points within buffer
    within_buffer = dist <= BUFFER_KM
    count = within_buffer.sum()
    print(f"    ({elat:.3f}, {elng:.3f}) → {count} grid points within {BUFFER_KM}km")

    df.loc[within_buffer, 'nasa_landslide']  = 1
    df.loc[within_buffer & (dist < df['nasa_nearest_event_km']),
           'nasa_nearest_event_km'] = dist[within_buffer & (dist < df['nasa_nearest_event_km'])]
    df.loc[within_buffer, 'nasa_trigger'] = event['landslide_trigger']

nasa_positive = df['nasa_landslide'].sum()
print(f"\n  Grid points marked as landslide (NASA): {nasa_positive}")

# ── Update Landslide Label ─────────────────────────────────
print(f"\n  Updating landslide labels...")

if 'landslide_label' in df.columns:
    original_positive = df['landslide_label'].sum()
    # NASA verified → override to 1
    df.loc[df['nasa_landslide'] == 1, 'landslide_label'] = 1
    new_positive = df['landslide_label'].sum()
    print(f"  Landslide labels before: {original_positive}")
    print(f"  Landslide labels after : {new_positive}")
    print(f"  New verified positives : {new_positive - original_positive}")
else:
    df['landslide_label'] = df['nasa_landslide']
    print(f"  Created landslide_label: {df['landslide_label'].sum()} positives")

# ── Save ───────────────────────────────────────────────────
df.to_csv(OUTPUT_CSV, index=False)

print(f"\n{'='*55}")
print(f"  INTEGRATION COMPLETE")
print(f"{'='*55}")
print(f"  Output : {OUTPUT_CSV}")
print(f"  Rows   : {len(df)}")
print(f"  NASA-verified landslide points: {nasa_positive}")
print(f"\n  Citation for research paper:")
print(f"  Kirschbaum, D. B., et al. (2010). A global landslide")
print(f"  catalog for hazard applications. Natural Hazards,")
print(f"  52(3), 561-575. doi:10.1007/s11069-009-9401-4")
