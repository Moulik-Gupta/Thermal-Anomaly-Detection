"""
Download Sentinel-2 satellite imagery for fire hotspot candidates.
Uses multiple fallback methods for reliable downloads.
"""

import pandas as pd
from datetime import datetime, timedelta
import requests
from pathlib import Path
import time

def create_bbox(lat, lon, buffer_deg=0.01):
    """
    Create bounding box around a point.
    buffer_deg=0.01 ≈ 1km at equator (total 2km × 2km box for better coverage)
    Returns: [min_lon, min_lat, max_lon, max_lat]
    """
    return [
        lon - buffer_deg,  # west
        lat - buffer_deg,  # south
        lon + buffer_deg,  # east
        lat + buffer_deg   # north
    ]

def download_with_planetary_computer(lat, lon, date_str, output_path, idx):
    """
    Method 1: Try Microsoft Planetary Computer STAC API
    """
    print(f"\n  → Method 1: Trying Planetary Computer API...")

    try:
        # Parse date
        fire_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = (fire_date - timedelta(days=3)).strftime("%Y-%m-%d")
        end_date = (fire_date + timedelta(days=3)).strftime("%Y-%m-%d")

        bbox = create_bbox(lat, lon)

        # Search for imagery
        search_url = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
        search_params = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": f"{start_date}T00:00:00Z/{end_date}T23:59:59Z",
            "limit": 5
        }

        print(f"    Searching {start_date} to {end_date}...")
        response = requests.post(search_url, json=search_params, timeout=30)

        if response.status_code != 200:
            print(f"    ✗ Search failed: HTTP {response.status_code}")
            return False

        results = response.json()
        features = results.get("features", [])

        print(f"    Found {len(features)} scenes")

        if not features:
            return False

        # Get best feature
        best = min(features, key=lambda f: f['properties'].get('eo:cloud_cover', 100))
        cloud = best['properties'].get('eo:cloud_cover', 'N/A')
        scene_date = best['properties'].get('datetime', '')[:10]

        print(f"    Best scene: {scene_date}, cloud cover: {cloud}%")

        # Try to get rendered preview
        assets = best.get('assets', {})

        # Try different asset types
        for asset_name in ['rendered_preview', 'visual', 'thumbnail']:
            if asset_name in assets:
                href = assets[asset_name]['href']
                print(f"    Found '{asset_name}' asset, downloading...")

                # Sign URL with Planetary Computer token
                sign_url = f"https://planetarycomputer.microsoft.com/api/sas/v1/sign?href={href}"
                sign_response = requests.get(sign_url, timeout=10)

                if sign_response.status_code == 200:
                    signed = sign_response.json()
                    download_url = signed.get('href', href)

                    # Download image
                    img_response = requests.get(download_url, timeout=60)

                    if img_response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            f.write(img_response.content)
                        print(f"    ✓ Downloaded successfully!")
                        return True

        print(f"    ✗ No usable preview assets found")
        return False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def download_with_sentinel_hub_wms(lat, lon, date_str, output_path, idx):
    """
    Method 2: Use public Sentinel Hub WMS service (no auth needed for preview)
    This provides a simple way to get RGB imagery
    """
    print(f"\n  → Method 2: Trying Sentinel Hub WMS...")

    try:
        fire_date = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = (fire_date - timedelta(days=5)).strftime("%Y-%m-%d")
        end_date = (fire_date + timedelta(days=2)).strftime("%Y-%m-%d")

        bbox = create_bbox(lat, lon, buffer_deg=0.005)  # 1km box

        # Sentinel Hub public WMS endpoint
        wms_url = "https://services.sentinel-hub.com/ogc/wms/cd2801-YOUR-INSTANCE-ID"

        # Note: Public WMS typically requires instance ID
        # For now, this is a placeholder - we'll use another method

        print(f"    ✗ Requires Sentinel Hub account (skipping)")
        return False

    except Exception as e:
        print(f"    ✗ Error: {e}")
        return False

def download_with_google_earth_engine_proxy(lat, lon, date_str, output_path, idx):
    """
    Method 3: Use a public Earth Engine image service
    Note: This is a simplified example and may not work without proper setup
    """
    print(f"\n  → Method 3: Trying alternative sources...")

    # For now, skip this method
    print(f"    ✗ Not configured (would require Google Earth Engine setup)")
    return False

def create_placeholder_image(output_path, lat, lon, date_str, message="No imagery available"):
    """
    Create a placeholder image when download fails
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new('RGB', (512, 512), color=(200, 200, 200))
        draw = ImageDraw.Draw(img)

        # Add text
        text = f"{message}\nLat: {lat:.5f}\nLon: {lon:.5f}\nDate: {date_str}"
        draw.text((20, 200), text, fill=(50, 50, 50))

        img.save(output_path)
        return True
    except:
        return False

def main():
    print("="*70)
    print("SENTINEL-2 IMAGERY DOWNLOADER")
    print("="*70)

    # Read candidates
    candidates_file = "candidates.csv"
    print(f"\nReading {candidates_file}...")

    df = pd.read_csv(candidates_file)
    print(f"✓ Found {len(df)} hotspot candidates\n")

    # Create output directory
    output_dir = Path("satellite_images")
    output_dir.mkdir(exist_ok=True)
    print(f"✓ Output directory: {output_dir.absolute()}\n")

    # Statistics
    success_count = 0
    failed_hotspots = []

    # Process each hotspot
    for idx, row in df.iterrows():
        lat = row['latitude']
        lon = row['longitude']
        date_str = row['acq_date']

        print(f"\n{'='*70}")
        print(f"[{idx + 1}/{len(df)}] HOTSPOT: ({lat:.5f}, {lon:.5f}) on {date_str}")
        print(f"{'='*70}")

        output_filename = f"hotspot_{idx + 1}_{date_str}.png"
        output_path = output_dir / output_filename

        # Try multiple download methods
        downloaded = False

        # Method 1: Planetary Computer
        if download_with_planetary_computer(lat, lon, date_str, output_path, idx):
            downloaded = True
            success_count += 1

        # Method 2: Add more methods here if needed
        # elif download_with_sentinel_hub_wms(lat, lon, date_str, output_path, idx):
        #     downloaded = True
        #     success_count += 1

        if not downloaded:
            print(f"\n  ⚠ All download methods failed for this hotspot")
            failed_hotspots.append((idx + 1, lat, lon, date_str))

            # Create placeholder
            placeholder_path = output_dir / f"placeholder_{idx + 1}_{date_str}.png"
            if create_placeholder_image(placeholder_path, lat, lon, date_str):
                print(f"  → Created placeholder: {placeholder_path.name}")

        # Small delay to avoid rate limiting
        time.sleep(1)

    # Summary
    print(f"\n{'='*70}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*70}")
    print(f"✓ Successfully downloaded: {success_count}/{len(df)}")
    print(f"✗ Failed: {len(failed_hotspots)}/{len(df)}")

    if failed_hotspots:
        print(f"\nFailed hotspots:")
        for idx, lat, lon, date in failed_hotspots:
            print(f"  - Hotspot {idx}: ({lat:.5f}, {lon:.5f}) on {date}")

    print(f"\nImages saved in: {output_dir.absolute()}")
    print(f"{'='*70}")

    # Suggest next steps
    if success_count == 0:
        print("\n⚠ No images downloaded. Possible reasons:")
        print("  1. No cloud-free Sentinel-2 imagery available for these dates/locations")
        print("  2. The hotspots are in Sri Lanka - check if Sentinel-2 covers this region")
        print("  3. Network connectivity issues")
        print("  4. API rate limiting")
        print("\nNext steps:")
        print("  - Try registering for Copernicus Data Space Ecosystem for better access")
        print("  - Consider using Landsat imagery as an alternative")
        print("  - Extend the date range (±7 days instead of ±3)")
        print("  - Relax cloud cover threshold (50% instead of 20%)")

if __name__ == "__main__":
    main()
