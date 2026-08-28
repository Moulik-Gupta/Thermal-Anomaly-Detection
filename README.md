# Thermal Anomaly Detection System

A Python-based thermal anomaly detection system for SIH 2026 that fetches and visualizes fire detection data from NASA FIRMS (Fire Information for Resource Management System) API.

## Features

- Fetches real-time thermal anomaly data from NASA VIIRS satellite
- Filters candidate hotspots based on brightness temperature (>350K)
- Generates interactive maps with Folium
- Covers India region with configurable bounding box
- Exports data to CSV for further analysis

## Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd SIH
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install requests pandas folium
```

4. Get your NASA FIRMS API key:
   - Visit https://firms.modaps.eosdis.nasa.gov/map_keys/
   - Replace the API_KEY in `thermal_anomaly/fetch_firms.py` with your key

## Usage

Run the thermal anomaly detection script:
```bash
cd thermal_anomaly
python fetch_firms.py
```

This will generate:
- `firms_data.csv` - All fire detections
- `candidates.csv` - Top hotspots filtered by brightness
- `hotspot_map.html` - Interactive visualization map

Open `hotspot_map.html` in your browser to explore the detected hotspots.

## Configuration

Edit `fetch_firms.py` to customize:
- `SOURCE` - Satellite data source (default: VIIRS_NOAA20_NRT)
- `DAYS` - Number of days to fetch (default: 5)
- `india_bbox` - Geographic bounding box for the region

## Project Structure

```
SIH/
├── thermal_anomaly/
│   └── fetch_firms.py    # Main script
├── .gitignore
└── README.md
```

## SIH 2026

This project is developed for Smart India Hackathon 2026.

## License

MIT
