# logic/monthly_distance.py
import pandas as pd
from geopy.distance import geodesic
from collections import defaultdict
import math

def calculate_total_distance_for_day(coords):
    """
    Calculate total distance (in km) following the given visiting order.
    """
    if not coords or len(coords) <= 1:
        return 0.0

    total_km = 0.0
    for i in range(len(coords) - 1):
        try:
            total_km += geodesic(coords[i], coords[i + 1]).km
        except Exception:
            # if geodesic fails for a pair, skip it
            continue
    return round(total_km, 2)


def calculate_monthly_distance(file_path):
    """
    Reads the uploaded route Excel and calculates:
    - total distance per day (following VISIT_ORDER)
    - total monthly distance per SO
    Returns a JSON-serializable dict.
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return {"status": "error", "message": f"Failed to read Excel file: {e}"}

    required_cols = [
        "SO NAME", "SO_ERP_ID",
        "Latitude", "Longitude",
        "WEEK", "DAY", "VISIT_ORDER"
    ]
    for col in required_cols:
        if col not in df.columns:
            return {"status": "error", "message": f"Missing column: {col}"}

    # Drop rows with missing coordinates
    df = df.dropna(subset=["Latitude", "Longitude"])

    # Ensure VISIT_ORDER is numeric so sorting works
    if "VISIT_ORDER" in df.columns:
        try:
            df["VISIT_ORDER"] = pd.to_numeric(df["VISIT_ORDER"], errors="coerce")
        except Exception:
            pass

    # Sort by SO / week / day / visit_order
    df = df.sort_values(by=["SO NAME", "SO_ERP_ID", "WEEK", "DAY", "VISIT_ORDER"])

    day_groups = df.groupby(["SO NAME", "SO_ERP_ID", "WEEK", "DAY"], sort=False)
    results = defaultdict(float)
    detailed = []

    for (so_name, so_erp, week, day), group in day_groups:
        coords = list(zip(group["Latitude"].astype(float), group["Longitude"].astype(float)))
        total_km = calculate_total_distance_for_day(coords)
        results[(so_name, so_erp)] += total_km

        detailed.append({
            "SO NAME": so_name,
            "SO_ERP_ID": so_erp,
            "WEEK": int(week) if not pd.isna(week) else week,
            "DAY": str(day),
            "DISTANCE_KM": float(total_km),
            "OUTLETS_VISITED": int(len(coords))
        })

    total_summary = [
        {"SO NAME": so, "SO_ERP_ID": erp, "TOTAL_MONTHLY_DISTANCE_KM": round(dist, 2)}
        for (so, erp), dist in results.items()
    ]

    # Optional: sort summary alphabetically by SO NAME
    total_summary = sorted(total_summary, key=lambda x: (str(x.get("SO NAME", "")).lower(), str(x.get("SO_ERP_ID",""))))

    return {
        "status": "success",
        "summary": total_summary,
        "daily_breakdown": detailed
    }
