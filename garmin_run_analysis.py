#!/usr/bin/env python3
import json
import math
from datetime import datetime
from garminconnect import Garmin

EMAIL = "tong_li@mac.com"
PASSWORD = "G0running2022!"

print("Logging into Garmin Connect...")
client = Garmin(EMAIL, PASSWORD)
client.login()

print("Fetching activities...")
activities = client.get_activities(0, 20)

# Filter to running activities only
running = [a for a in activities if a.get("activityType", {}).get("typeKey", "") in ("running", "track_running", "trail_running", "treadmill_running")]
runs = running[:5]

if not runs:
    print("No running activities found in last 20 activities.")
    exit(1)

print(f"Found {len(runs)} runs. Fetching details...")

processed = []
for r in runs:
    act_id = r["activityId"]
    details = client.get_activity(act_id)

    # Basic metrics from summary
    name = r.get("activityName", "Run")
    date_str = r.get("startTimeLocal", "")
    try:
        date = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S").strftime("%b %d, %Y")
    except:
        date = date_str[:10]

    distance_m = r.get("distance", 0)
    distance_km = distance_m / 1000

    duration_s = r.get("duration", 0)
    duration_min = duration_s / 60

    avg_hr = r.get("averageHR", None)
    max_hr = r.get("maxHR", None)

    # Pace in min/km
    if distance_km > 0:
        pace_sec_per_km = (duration_s / distance_km)
        pace_min = int(pace_sec_per_km // 60)
        pace_sec = int(pace_sec_per_km % 60)
        pace_str = f"{pace_min}:{pace_sec:02d}"
        pace_val = pace_sec_per_km / 60  # float min/km for charting
    else:
        pace_str = "N/A"
        pace_val = None

    # Elevation
    elev_gain = r.get("elevationGain", 0)

    # Cadence
    avg_cadence = r.get("averageRunningCadenceInStepsPerMinute", None)

    processed.append({
        "id": act_id,
        "name": name,
        "date": date,
        "distance_km": round(distance_km, 2),
        "duration_min": round(duration_min, 1),
        "pace_str": pace_str,
        "pace_val": round(pace_val, 3) if pace_val else None,
        "avg_hr": int(avg_hr) if avg_hr else None,
        "max_hr": int(max_hr) if max_hr else None,
        "elev_gain": round(elev_gain, 0) if elev_gain else 0,
        "cadence": int(avg_cadence) if avg_cadence else None,
    })

# Trend analysis
paces = [r["pace_val"] for r in processed if r["pace_val"]]
hrs = [r["avg_hr"] for r in processed if r["avg_hr"]]

# Runs are ordered newest first — reverse for trend (oldest to newest)
paces_chron = list(reversed(paces))
hrs_chron = list(reversed(hrs))

def trend(vals):
    if len(vals) < 2:
        return "flat"
    n = len(vals)
    x_mean = (n - 1) / 2
    y_mean = sum(vals) / n
    num = sum((i - x_mean) * (vals[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0
    return slope

pace_trend = trend(paces_chron)
hr_trend = trend(hrs_chron)

pace_trend_pct = ((paces_chron[-1] - paces_chron[0]) / paces_chron[0] * 100) if len(paces_chron) >= 2 else 0
hr_trend_pct = ((hrs_chron[-1] - hrs_chron[0]) / hrs_chron[0] * 100) if len(hrs_chron) >= 2 else 0

# Pace improving = negative (faster), HR improving = going down
pace_improving = pace_trend < 0
hr_improving = hr_trend < 0

analysis_lines = []
if pace_improving:
    analysis_lines.append(f"Pace is trending <span class='good'>faster</span> ({abs(pace_trend_pct):.1f}% improvement over last 5 runs).")
else:
    analysis_lines.append(f"Pace is trending <span class='warn'>slower</span> ({abs(pace_trend_pct):.1f}% change over last 5 runs).")

if hr_improving:
    analysis_lines.append(f"Heart rate is trending <span class='good'>down</span> ({abs(hr_trend_pct):.1f}% decrease), indicating improved aerobic efficiency.")
else:
    analysis_lines.append(f"Heart rate is trending <span class='warn'>up</span> ({abs(hr_trend_pct):.1f}% increase) — monitor recovery and load.")

if pace_improving and hr_improving:
    analysis_lines.append("Running faster at a lower HR is a strong sign of <span class='good'>aerobic fitness gains</span>.")
elif not pace_improving and not hr_improving:
    analysis_lines.append("Both pace and HR are moving in the wrong direction — consider a recovery week.")
elif pace_improving and not hr_improving:
    analysis_lines.append("Faster paces at a higher HR could indicate fatigue accumulation or higher intensity training.")
else:
    analysis_lines.append("Lower HR but slower pace may reflect a deliberate easy/recovery week.")

# Save data for HTML
output = {
    "runs": processed,
    "analysis": analysis_lines,
    "pace_trend_pct": round(pace_trend_pct, 1),
    "hr_trend_pct": round(hr_trend_pct, 1),
    "pace_improving": pace_improving,
    "hr_improving": hr_improving,
}

with open("/tmp/garmin_runs.json", "w") as f:
    json.dump(output, f, indent=2)

print("Done. Data saved to /tmp/garmin_runs.json")
