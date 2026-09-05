# FIRMS Thermal Detection Dashboard

Streamlit dashboard jo NASA FIRMS API se thermal anomaly (hot-spot) detections
fetch karke interactive map + filters ke saath dikhata hai.

## Setup (Windows / VS Code)

1. **Virtual environment banao** (project folder ke andar):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Dependencies install karo:**
   ```
   pip install -r requirements.txt
   ```

3. **API key set karo** — `.env.example` ko copy karke `.env` banao:
   ```
   copy .env.example .env
   ```
   Phir `.env` file kholo aur apni real FIRMS MAP_KEY daalo:
   ```
   FIRMS_MAP_KEY=abcd1234yourrealkey
   ```
   (Key nahi hai to https://firms.modaps.eosdis.nasa.gov/api/map_key/ se free le lo)

4. **App run karo:**
   ```
   streamlit run app.py
   ```

   Browser mein automatically khul jayega (usually `http://localhost:8501`).

## Features

- Preset areas (India, World, USA, Europe, custom bounding box)
- VIIRS/MODIS source selection
- 1-10 din tak ka day range
- FRP, confidence, aur day/night filters
- Interactive Folium map (color-coded by FRP intensity)
- Raw data table + CSV export
- API quota checker

## Note

Yeh raw FIRMS data dikhata hai — abhi tak koi industrial vs natural
classification nahi hai. Wo agle development phase mein add hoga
(OSM facility matching, persistence scoring, ML classification).
