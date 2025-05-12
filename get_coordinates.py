#!/usr/bin/env python3
import requests
import pandas as pd
import time


def geocode_address(
    addr: str, session: requests.Session
) -> tuple[float | None, float | None]:
    """
    Geocode a single address string using Nominatim.
    Returns (latitude, longitude) or (None, None) on failure.
    """
    try:
        response = session.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": addr, "format": "json", "limit": 1},
            timeout=10,
        )
        data = response.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        print(f"Error geocoding '{addr}': {e}")
    return None, None


def main():
    # 1) Load your existing CSV
    df = pd.read_csv("hotels_uk.csv")
    total = len(df)
    print(f"Starting geocode of {total} addresses…")

    # 2) Prepare session with a custom User-Agent
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "BWGeocoder/1.0 (+https://yourdomain.example)"}
    )

    # 3) Iterate and geocode
    lats, lons = [], []
    for idx, row in df.iterrows():
        addr = f"{row['Street']}, {row['City']}, {row['Postcode']}"
        print(f"[{idx+1}/{total}] Geocoding: {addr}")
        lat, lon = geocode_address(addr, session)
        lats.append(lat)
        lons.append(lon)
        time.sleep(1)  # Nominatim rate limit: 1 request per second

    # 4) Append coordinates and save
    df["Latitude"] = lats
    df["Longitude"] = lons
    df.to_csv("hotels_with_coords.csv", index=False, encoding="utf-8-sig")
    print("✅ Saved hotels_with_coords.csv with Latitude/Longitude columns.")


if __name__ == "__main__":
    main()
