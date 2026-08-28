import requests
import pandas as pd
import folium
from io import StringIO
import sys

try:
    from config import API_KEY, SOURCE, DAYS, INDIA_BBOX
except ImportError:
    print("\n[ERROR] config.py not found!")
    print("Please create config.py from config.example.py")
    print("and add your NASA FIRMS API key.")
    sys.exit(1)

def fetch_firms_data():
    """Fetch thermal anomaly data from NASA FIRMS API."""

    print("=" * 60)
    print("  SIH 2026 - Thermal Anomaly Detection System")
    print("  NASA FIRMS Data Fetcher")
    print("=" * 60)

    if API_KEY == "YOUR_API_KEY_HERE":
          print("\n[ERROR] Please replace 'YOUR_API_KEY_HERE' in config.py")
          print("        with your actual FIRMS API key.")
          print("        Get one at: https://firms.modaps.eosdis.nasa.gov/map_keys/")
          sys.exit(1)

      # Build the API URL using area endpoint instead of country
    url = (
          f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
          f"{API_KEY}/{SOURCE}/{INDIA_BBOX}/{DAYS}"
      )

    print(f"\n[1/4] Fetching data from NASA FIRMS...")
    print(f"      Source   : {SOURCE}")
    print(f"      Region   : India (bounding box)")
    print(f"      Period   : Last {DAYS} days")
    print(f"      API URL: {url[:80]}...")
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] Failed to fetch data: {e}")
        print(f"\n[DEBUG] Full URL: {url}")
        print(f"[DEBUG] Response status: {response.status_code if'response' in locals() else 'N/A'}")
        if'response' in locals():
            print(f"[DEBUG] Response text: {response.text[:300]}")
        sys.exit(1)
    # Parse CSV response
    try:
        df = pd.read_csv(StringIO(response.text))
    except Exception as e:
        print(f"\n[ERROR] Failed to parse response: {e}")
        print(f"        Response preview: {response.text[:200]}")
        sys.exit(1)
    if len(df) == 0:
        print(f"\n[WARNING] No fire detections found for the specified period.")
        print(f"           This could mean no fires were detected in India in the last {DAYS} days.")
        sys.exit(0)
    print(f"      Records  : {len(df)} fire detections found")
    # ----------------------------------------------------------
    # Save raw data
    # ----------------------------------------------------------
    print(f"\n[2/4] Saving raw data to firms_data.csv...")
    df.to_csv("firms_data.csv", index=False)
    print(f"      Saved {len(df)} records.")
    # ----------------------------------------------------------
    # Filter candidate hotspots (brightness temp > 350K)
    # ----------------------------------------------------------
    print(f"\n[3/4] Filtering candidate hotspots (brightness > 350K)...")
    # FIRMS uses 'bright_ti4' or 'brightness' column depending on source
    bright_col = None
    for col in ["bright_ti4", "brightness", "bright_ti5"]:
        if col in df.columns:
            bright_col = col
            break
    if bright_col is None:
        print("      [WARNING] No brightness column found. Using 'frp' instead.")
        bright_col = "frp"
        candidates = df.nlargest(min(8, len(df)), bright_col)
    else:
        candidates = df[df[bright_col] > 350]
        if len(candidates) > 8:
            candidates = candidates.nlargest(8, bright_col)
        elif len(candidates) < 5:
            print(f"      Only {len(candidates)} hotspots > 350K.")
            print(f"      Expanding to top 5 by {bright_col}...")
            candidates = df.nlargest(min(5, len(df)), bright_col)
    candidates.to_csv("candidates.csv", index=False)
    print(f"      Saved {len(candidates)} candidate hotspots to candidates.csv")
    # ----------------------------------------------------------
    # Create interactive map
    # ----------------------------------------------------------
    print(f"\n[4/4] Creating interactive hotspot map...")
    # Center map on India
    india_center = [22.5, 78.5]
    m = folium.Map(location=india_center, zoom_start=5, tiles="CartoDB dark_matter")
    # Add all fire detections as small circles
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=2,
            color="orange",
            fill=True,
            fill_opacity=0.4,
            popup=f"Lat: {row['latitude']}, Lon: {row['longitude']}"
        ).add_to(m)
    # Highlight candidates with larger red markers
    for _, row in candidates.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=0.8,
            popup=(
                f"<b>CANDIDATE HOTSPOT</b><br>"
                f"Lat: {row['latitude']}<br>"
                f"Lon: {row['longitude']}<br>"
                f"{bright_col}: {row[bright_col]}"
            )
        ).add_to(m)
    # Add legend
    legend_html = """
    <div style="position:fixed; bottom:30px; left:30px; z-index:1000;
                background:rgba(0,0,0,0.8); padding:15px; border-radius:8px;
                color:white; font-family:Arial; font-size:13px;">
        <b>SIH 2026 - Thermal Anomaly Map</b><br><br>
        <span style="color:orange;">&#9679;</span> Fire Detection<br>
        <span style="color:red;">&#9679;</span> Candidate Hotspot (>350K)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    m.save("hotspot_map.html")
    print(f"      Saved interactive map to hotspot_map.html")
    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total fire detections : {len(df)}")
    print(f"  Candidate hotspots    : {len(candidates)}")
    print(f"  Date range            : Last {DAYS} days")
    print(f"  Brightness column     : {bright_col}")
    print(f"\n  Output files:")
    print(f"    - firms_data.csv     (all detections)")
    print(f"    - candidates.csv     (top hotspots)")
    print(f"    - hotspot_map.html   (interactive map)")
    print(f"\n  Open hotspot_map.html in your browser to explore!")
    print("=" * 60)
if __name__ == "__main__":
      fetch_firms_data()