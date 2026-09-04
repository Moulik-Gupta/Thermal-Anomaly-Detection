# Thermal Anomaly Detection System

A comprehensive thermal anomaly detection system for SIH 2026 that combines NASA FIRMS fire detection data with Sentinel-2 satellite imagery and AI-powered fire classification.

## Features

### 🔥 Day 1: FIRMS Data Collection
- Fetches real-time thermal anomaly data from NASA VIIRS satellite
- Filters candidate hotspots based on brightness temperature (>350K)
- Generates interactive maps with Folium
- Covers India region with configurable bounding box
- Exports data to CSV for further analysis

### 🛰️ Day 2: Satellite Imagery Acquisition
- Downloads high-resolution Sentinel-2 satellite imagery for each hotspot
- Automatically retrieves imagery from ESA Copernicus Data Space
- Extracts RGB bands and generates true-color images
- Handles cloud cover filtering and image quality validation
- Creates visual summaries of downloaded imagery

### 🤖 Day 3: AI-Powered Fire Detection
- Uses pre-trained Vision Transformer (ViT) model for fire classification
- Classifies each satellite image as "Fire" or "No Fire" with confidence scores
- Fallback to brightness temperature threshold when model unavailable
- Generates comprehensive classification reports with visualizations
- Exports results to CSV for dashboard integration

## Setup

### Prerequisites
- Python 3.8 or higher
- NASA FIRMS API key ([Get one here](https://firms.modaps.eosdis.nasa.gov/map_keys/))
- Copernicus Data Space account (for Sentinel-2 imagery)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Moulik-Gupta/Thermal-Anomaly-Detection.git
cd SIH
```

2. Create a virtual environment:
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your API credentials:
   - Copy `thermal_anomaly/config.example.py` to `thermal_anomaly/config.py`
   - Add your NASA FIRMS API key
   - (Optional) Add Copernicus credentials for satellite imagery download

## Usage

### Day 1: Fetch FIRMS Fire Detection Data

```bash
cd thermal_anomaly
python fetch_firms.py
```

**Outputs:**
- `firms_data.csv` - All fire detections from VIIRS
- `candidates.csv` - Filtered hotspots (brightness > 350K)
- `hotspot_map.html` - Interactive map visualization

### Day 2: Download Satellite Imagery

```bash
python download_sentinel2.py
```

**Outputs:**
- `satellite_images/` - Directory containing RGB images for each hotspot
- `satellite_images_summary.png` - Visual grid of all downloaded images

### Day 3: Run Fire Detection Classifier

```bash
python classify_fire.py
```

**Outputs:**
- `classification_results.csv` - Fire/No Fire classifications with confidence scores
- `classification_summary.txt` - Text report of results
- `classification_report.png` - Visual grid showing predictions

## How It Works

### Pipeline Overview

```
NASA FIRMS → Filter Hotspots → Download Imagery → AI Classification → Dashboard
   (Day 1)        (Day 1)           (Day 2)            (Day 3)         (Day 4)
```

1. **Thermal Anomaly Detection**: Fetch VIIRS satellite data from NASA FIRMS API, identifying thermal hotspots with brightness temperature > 350K
2. **Satellite Imagery**: Download corresponding Sentinel-2 RGB imagery from ESA Copernicus for visual analysis
3. **AI Classification**: Run pre-trained ViT fire detection model (`EdBianchi/vit-fire-detection`) on each image
4. **Results**: Generate comprehensive reports with classifications, confidence scores, and visualizations

## Configuration

Edit `thermal_anomaly/config.py` to customize:
- `API_KEY` - Your NASA FIRMS API key
- `SOURCE` - Satellite data source (default: VIIRS_NOAA20_NRT)
- `DAYS` - Number of days to fetch (default: 5)
- `INDIA_BBOX` - Geographic bounding box for the region

## Project Structure

```
SIH/
├── thermal_anomaly/
│   ├── fetch_firms.py           # Day 1: FIRMS data fetching
│   ├── download_sentinel2.py    # Day 2: Satellite imagery download
│   ├── classify_fire.py         # Day 3: AI fire detection classifier
│   ├── verify_images.py         # Image validation utility
│   ├── config.example.py        # Configuration template
│   ├── config.py                # Your configuration (not tracked)
│   ├── firms_data.csv           # Raw FIRMS detections
│   ├── candidates.csv           # Filtered hotspots
│   ├── hotspot_map.html         # Interactive map
│   └── satellite_images/        # Downloaded Sentinel-2 images
├── .gitignore
├── requirements.txt
└── README.md
```

## Technologies Used

- **Data Sources**: NASA FIRMS API, ESA Copernicus Sentinel-2
- **AI/ML**: Hugging Face Transformers, PyTorch, Vision Transformer (ViT)
- **Data Processing**: Pandas, NumPy
- **Visualization**: Matplotlib, Folium
- **Image Processing**: Pillow, OpenCV, rasterio

## Results

### Sample Output (August 2026 Data)

- **Hotspots Detected**: 8 thermal anomalies across Sri Lanka region
- **Satellite Images**: 8 high-resolution Sentinel-2 RGB images downloaded
- **AI Classification**: 8/8 images classified with 99.8% average confidence
- **Detection Method**: Pre-trained ViT model (EdBianchi/vit-fire-detection)

### Key Findings

The system successfully distinguishes between thermal anomalies detected by VIIRS and actual visible fire signatures in RGB imagery. All hotspots showed high brightness temperatures (352-367K) but were classified as "No Fire" by the AI model, indicating the thermal signatures may be from industrial sources or subsided fires rather than active flames.

## Future Enhancements (Day 4+)

- 🎨 Interactive dashboard for real-time monitoring
- 📊 Time-series analysis of fire patterns
- 🗺️ Multi-region support with automated alerts
- 📱 Mobile-responsive web interface
- ☁️ Cloud deployment for continuous monitoring

## Contributing

This project is developed for Smart India Hackathon 2026. Contributions and suggestions are welcome!

## Acknowledgments

- NASA FIRMS for providing real-time fire detection data
- ESA Copernicus for Sentinel-2 satellite imagery
- Hugging Face for pre-trained fire detection models
- EdBianchi for the ViT fire detection model

## License

MIT

---

**Developed for Smart India Hackathon 2026** 🇮🇳
