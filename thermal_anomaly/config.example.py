# ============================================================
# NASA FIRMS API Configuration Template
# ============================================================
# 1. Copy this file and rename it to 'config.py'
# 2. Replace the placeholder with your actual FIRMS API key
# 3. Get your key at: https://firms.modaps.eosdis.nasa.gov/map_keys/
# ============================================================

API_KEY = "YOUR_API_KEY_HERE"

# FIRMS API settings
SOURCE = "VIIRS_NOAA20_NRT"  # Satellite data source
DAYS = 5                      # Number of days to fetch data for

# India bounding box: [lon_min, lat_min, lon_max, lat_max]
# India approximately: 6.5°N to 35.5°N, 68°E to 97.5°E
INDIA_BBOX = "68,6.5,97.5,35.5"
