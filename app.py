"""
NASA FIRMS Thermal Detection Dashboard - V39 (Hide Deploy, Keep Three Dots)

A Streamlit web app that pulls near-real-time fire/thermal anomaly data
from NASA's FIRMS API, displays it on an interactive map, and provides
basic analytics (daily counts, FRP distribution, hourly trends, alerts).
"""

import os
import re
import base64
from io import StringIO
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from dotenv import load_dotenv
import streamlit.components.v1 as components

# Load environment variables (e.g. FIRMS_MAP_KEY) from a local .env file, if present.
load_dotenv()

# --- Basic Streamlit page configuration ---
# Sets the browser tab title/icon, uses a wide layout, and collapses the
# default sidebar since this app builds its own custom nav bar instead.
st.set_page_config(
    page_title="FIRMS Thermal Detection Dashboard",

    layout="wide",
    initial_sidebar_state="collapsed",
)

# Base endpoint for NASA FIRMS "area" CSV API.
# Full request URL is built as: {FIRMS_BASE_URL}/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Satellite/sensor sources supported by FIRMS that this app lets the user pick from.
SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
]

# Preset bounding boxes (min_lon, min_lat, max_lon, max_lat) for quick region selection.
# "World" is a special FIRMS keyword rather than a bbox. "Custom" lets the user type their own.
PRESET_AREAS = {
    "India": "68,6,97,37",
    "World": "world",
    "South Asia": "60,5,100,40",
    "USA": "-125,24,-66,49",
    "Europe": "-10,35,30,60",
    "Custom (enter below)": None,
}


@st.cache_data(show_spinner=False)
def get_background_css(image_path: str) -> str:
    """
    Read a local background image, base64-encode it, and return a <style>
    block that sets it as the app's full-page background with a dark
    gradient overlay (for readability of white text on top of the image).

    Returns an empty string if the image file doesn't exist, so callers
    can safely skip injecting CSS in that case.
    """
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    ext = image_path.split(".")[-1].lower()
    # Normalize "jpg" to the correct MIME subtype "jpeg"; everything else is used as-is.
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(5,5,15,0.45), rgba(5,5,15,0.72)), url("data:image/{mime};base64,{encoded}");
            background-size: cover; background-position: center; background-attachment: fixed;
        }}
        </style>
        """


# Attempt to load and inject a background image (cached so it's only read/encoded once).
BACKGROUND_IMAGE_PATH = "assets/space-bg.jpg"
bg_css = get_background_css(BACKGROUND_IMAGE_PATH)
if bg_css:
    st.markdown(bg_css, unsafe_allow_html=True)

# ---------------------------------------------------------------
# HIDE DEPLOY BUTTON (BUT KEEP THE THREE DOTS)
# ---------------------------------------------------------------
# Streamlit's built-in "Deploy" button lives in the parent document (the
# app is rendered inside an iframe context in some setups), so we inject
# a small script that runs in the parent window, finds any <button> whose
# text is exactly "Deploy", and hides it. It's re-run periodically
# (setInterval) because Streamlit may re-render that button on reruns.
components.html(
    """
    <script>
    function hideDeployButton() {
        const root = window.parent && window.parent.document ? window.parent.document : document;
        const buttons = root.querySelectorAll('button');
        for (const btn of buttons) {
            const text = (btn.textContent || '').trim();
            if (text === 'Deploy') {
                btn.style.display = 'none';
            }
        }
    }
    setTimeout(hideDeployButton, 300);   // initial hide shortly after load
    setInterval(hideDeployButton, 2000); // keep re-hiding in case Streamlit re-renders it
    </script>
    """,
    height=0,       # invisible component; it only exists to run JS
    scrolling=False,
)

# ---------------------------------------------------------------
# GLOBAL CSS THEME
# ---------------------------------------------------------------
# Defines the dark "space" theme, the fixed/sticky top navbar, bold white
# text with shadows for contrast over the background image, metric/panel
# card styling, and a responsive block for phones/narrow screens.
st.markdown(
    """
    <style>
    /* Apple's official system-font stack (as used on apple.com): renders as
       San Francisco / SF Pro on Apple devices, with matching native-feeling
       fallbacks (Segoe UI on Windows, Roboto on Android, etc). */

    /* Overall app background: dark radial gradient (works even if the
       background image above fails to load). */
    .stApp {
        background-color: #0a0e1f;
        background-image: radial-gradient(180deg, #0a0e1f 0%, #0d1024 60%, #120a1e 100%);
        background-attachment: fixed;
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif;
    }
    
    /* Custom top navigation bar: fixed to the top of the viewport, spans the
       full width, semi-transparent with blur, sits above everything else. */
    .sticky-nav {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        z-index: 999999 !important;
        background-color: rgba(10, 12, 24, 0.92) !important;
        backdrop-filter: blur(15px) !important;
        border-bottom: 1px solid rgba(255, 107, 53, 0.35) !important;
        padding: 14px 0 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.6) !important;
    }

    /* Spread the logo and nav buttons evenly across the full width of the
       bar, with generous side padding and vertical centering. */
    .sticky-nav div[data-testid="stHorizontalBlock"] {
        justify-content: space-between !important;
        align-items: center !important;
        padding: 0 2.5rem !important;
        gap: 0.5rem !important;
    }
    
    /* Push main content down so it isn't hidden behind the fixed navbar,
       and cap the max width so content doesn't stretch too wide on large screens. */
    .main .block-container { 
        padding-top: 7rem !important;
        max-width: 1600px !important; 
    }

    /* Global typography: clean, moderately-weighted text with a soft
       shadow just enough for contrast over the dark/background-image backdrop. */
    html, body, [class*="css"], p, span, label, h1, h2, h3, h4, h5, h6, strong, b {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        font-size: 1rem !important; 
        font-weight: 500 !important;
        color: #FFFFFF !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.5) !important;
        letter-spacing: 0.01em !important;
    }

    /* Form controls (text inputs, select/multiselect boxes) match the same
       clean styling as the rest of the UI. */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: #FFFFFF !important;
    }

    /* Streamlit's built-in "Press Enter to apply" hint: by default it sits
       inside/overlapping the input box (and the password visibility icon).
       Push it below the field instead so it doesn't collide with the text. */
    div[data-testid="InputInstructions"] {
        position: absolute !important;
        top: 100% !important;
        right: 0 !important;
        margin-top: 6px !important;
        font-size: 0.75rem !important;
        opacity: 0.75 !important;
        white-space: nowrap !important;
    }
    div[data-testid="stTextInput"] {
        position: relative !important;
        margin-bottom: 1.6rem !important;
    }

    /* Restore Streamlit's own Material icon font for icons like the password
       show/hide "eye" toggle. Our global font-family override above (with
       !important) otherwise clobbers the icon font too, which breaks the
       icon ligature and makes it fall back to raw text (or nothing at all). */
    [data-testid="stIconMaterial"],
    .stTextInput button span,
    .stTextInput button svg {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        text-shadow: none !important;
        letter-spacing: normal !important;
        color: #E8E8EC !important;
        opacity: 1 !important;
        font-size: 1.1rem !important;
        -webkit-font-feature-settings: 'liga' !important;
        font-feature-settings: 'liga' !important;
    }
    .stTextInput button[kind] {
        color: #E8E8EC !important;
        opacity: 0.9 !important;
    }
    .stTextInput button[kind]:hover {
        opacity: 1 !important;
        color: #ff8a5c !important;
    }

    /* Regular action buttons (Fetch Dialogue, Fetch Latest Data, Cancel, etc.):
       restored to their original bold-white, default-background look. */
    div.stButton > button {
        font-size: 1rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        white-space: nowrap !important;
    }
    div.stButton > button:hover { color: #ff6b35 !important; }

    /* Nav buttons only (inside the sticky navbar): transparent background so
       they sit flush with the bar, with a subtle pill highlight on hover. */
    .sticky-nav div.stButton > button {
        font-weight: 600 !important;
        color: #E8E8EC !important;
        background-color: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 8px !important;
        padding: 0.5rem 1.1rem !important;
        box-shadow: none !important;
        transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    }
    .sticky-nav div.stButton > button:hover {
        color: #ff8a5c !important;
        background-color: rgba(255, 107, 53, 0.10) !important;
        border-color: rgba(255, 107, 53, 0.35) !important;
    }
    .sticky-nav div.stButton > button:focus:not(:active) {
        color: #ff8a5c !important;
        border-color: rgba(255, 107, 53, 0.35) !important;
    }

    /* Brand/logo text on the left of the navbar, styled in the orange accent color. */
    .navbar-left { font-size: 1.75rem !important; font-weight: 600 !important; color: #ff6b35; letter-spacing: -0.01em !important; text-shadow: 0 1px 3px rgba(0,0,0,0.5); }

    /* Streamlit's built-in st.metric() styling overrides. */
    div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #FF9466 !important;
    }

    /* Card-style container used for the left "Configuration" panel. */
    .config-box { background: rgba(10,12,24,0.85); border: 1px solid rgba(255,107,53,0.3); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .config-title { font-size: 1.15rem !important; font-weight: 600 !important; margin-bottom: 15px; color: #ffffff; }
    
    /* Card-style container used for the bottom metric boxes (Active Fires, Total FRP, Daily Change). */
    .bottom-metric-box { background: rgba(10,12,24,0.85); border: 1px solid rgba(255,107,53,0.25); border-radius: 12px; padding: 15px; text-align: center; color: white; margin-top: 10px; box-shadow: 0 8px 15px rgba(0,0,0,0.5); }
    .metric-label { font-size: 0.9rem !important; color: #ff9466; font-weight: 600 !important; }
    .metric-value { font-size: 2.2rem !important; font-weight: 700 !important; color: #ffffff !important; text-shadow: 0 1px 3px rgba(0,0,0,0.5) !important; }
    
    /* Generic card-style container used for the right-hand analytics/live-feed panels. */
    .side-panel { background: rgba(10,12,24,0.85); border: 1px solid rgba(255,107,53,0.25); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .panel-title { font-size: 1.15rem !important; font-weight: 700 !important; color: #ffffff; border-bottom: 1px solid rgba(255,107,53,0.3); padding-bottom: 8px; text-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    
    /* Tab label styling (e.g. "Detections per Day" / "FRP Distribution"). */
    .stTabs [data-baseweb="tab"] { font-size: 1rem !important; font-weight: 600 !important; }
    
    /* Scrollable "Live Data" feed box: fixed max height with its own scrollbar. */
    .live-feed { max-height: 250px; overflow-y: auto; font-size: 0.88rem !important; color: #ffffff !important; line-height: 1.9; font-weight: 500 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    .live-feed b { color: #ffd93d !important; font-weight: 600 !important; }
    
    /* Footer bar shown at the bottom of every page except "About". */
    .footer { margin-top: 30px; border-top: 1px solid rgba(255,107,53,0.3); padding-top: 10px; font-size: 0.85rem !important; color: #FFFFFF !important; font-weight: 500 !important; text-shadow: 0 1px 2px rgba(0,0,0,0.4); }
    
    /* Hide Streamlit's default sidebar entirely — this app uses a custom top navbar instead. */
    section[data-testid="stSidebar"] { display: none; }

    /* ============================================================
       MOBILE RESPONSIVE — applies on phones/narrow screens
       ============================================================ */
    @media (max-width: 768px) {
        /* Navbar: stop fighting for space, let it wrap onto 2 lines
           and stop being position:fixed (fixed+wrap = overlap bugs) */
        .sticky-nav {
            position: static !important;
            padding: 8px 10px !important;
        }
        .main .block-container {
            padding-top: 1.2rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        /* Let the row of nav buttons wrap instead of squeezing/overflowing */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            row-gap: 6px !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: fit-content !important;
            flex: 1 1 auto !important;
        }
        .navbar-left {
            font-size: 1.25rem !important;
            width: 100%;
            text-align: center;
            margin-bottom: 4px;
        }
        div.stButton > button {
            font-size: 0.8rem !important;
            padding: 0.35rem 0.5rem !important;
        }

        /* Shrink the wall-of-text font sizing for small screens */
        html, body, [class*="css"], p, span, label, h1, h2, h3, h4, h5, h6, strong, b {
            font-size: 0.92rem !important;
        }

        /* Metrics: smaller numbers so 4-across rows don't overflow */
        div[data-testid="stMetricValue"] { font-size: 1.5rem !important; }
        div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
        .metric-value { font-size: 1.7rem !important; }
        .metric-label { font-size: 0.8rem !important; }

        .config-box, .side-panel, .bottom-metric-box { padding: 10px !important; }
        .config-title, .panel-title { font-size: 1.05rem !important; }

        /* Live feed: slightly shorter so it doesn't dominate a phone screen */
        .live-feed { max-height: 180px !important; font-size: 0.8rem !important; }
    }

    @media (max-width: 480px) {
        /* Extra-narrow phones: metrics stack 2-per-row instead of 4 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            flex: 1 1 45% !important;
        }
        .navbar-left { font-size: 1.1rem !important; }
        div[data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Session state initialization ---
# "page" tracks which of the custom nav tabs is currently active.
# "source" tracks the currently selected satellite/sensor source.
if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "source" not in st.session_state: st.session_state.source = SOURCES[0]


@st.dialog("🚀 Fetch Data Options")
def open_fetch_dialog():
    """
    Modal dialog that summarizes the user's currently selected fetch
    settings (satellite, day range, region, day/night) and lets them
    either trigger a fresh data fetch (clearing the cache and stored
    dataframe so the app re-fetches on rerun) or cancel out.
    """
    st.write("Review your current settings and fetch fresh thermal data:")
    st.markdown(f"**🛰️ Satellite:** {st.session_state.source}")
    st.markdown(f"**📅 Day Range:** {st.session_state.get('day_range', 5)} days")
    area_choice = st.session_state.get('area_choice', "India")
    st.markdown(f"**🌍 Region:** {area_choice}")
    selected_dn = st.session_state.get('selected_dn', ['D', 'N'])
    st.markdown(f"**🌗 Day/Night:** {', '.join(selected_dn)}")
    st.divider()
    
    if st.button("⬇️ Fetch Latest Data", use_container_width=True, type="primary"):
        # Invalidate the cached API response and clear the stored dataframe
        # so the main page logic re-fetches fresh data on the next run.
        fetch_firms_data.clear()
        st.session_state.df = None
        st.rerun()
    
    if st.button("Cancel", use_container_width=True):
        st.rerun()

# ---------------------------------------------------------------
# FIXED NAVBAR
# ---------------------------------------------------------------
# Renders the custom top nav: a logo/title on the left and five buttons
# that switch the "page" stored in session state and trigger a rerun.
# The logo and buttons are spread across the full navbar width via the
# "justify-content: space-between" rule on .sticky-nav's flex row (CSS above),
# so no manual spacer column is needed here.
with st.container():
    st.markdown('<div class="sticky-nav">', unsafe_allow_html=True)
    col_logo, col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns([2.2, 1, 1, 1, 1, 1])
    with col_logo:
        st.markdown('<div class="navbar-left"> THERMOWATCH</div>', unsafe_allow_html=True)
    with col_b1:
        if st.button("Dashboard"): st.session_state.page = "Dashboard"; st.rerun()
    with col_b2:
        if st.button("Data Archives"): st.session_state.page = "Data Archives"; st.rerun()
    with col_b3:
        if st.button("Analysis Tools"): st.session_state.page = "Analysis Tools"; st.rerun()
    with col_b4:
        if st.button("Alerts"): st.session_state.page = "Alerts"; st.rerun()
    with col_b5:
        if st.button("About"): st.session_state.page = "About"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def format_time_ampm(value):
    """
    Normalize a FIRMS 'acq_time' value into a human-friendly 12-hour
    AM/PM string.

    FIRMS times can arrive in a few different raw shapes, e.g.:
      - bare numbers like 1345 (meaning 13:45) or 930 (meaning 9:30)
      - numbers that are actually already an hour (0-24)
      - strings that already contain "HH:MM"
    This function tries to handle all of those, falling back to
    returning the raw string unchanged if nothing matches.
    """
    if pd.isna(value): return ""
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none"}: return ""
    if raw.endswith('.0'): raw = raw[:-2]  # strip trailing ".0" from float-like strings
    
    if raw.isdigit():
        num = int(raw)
        if 0 <= num <= 24:
            # Small numbers (0-24) are treated as a bare hour with no minutes.
            hour, minute = num, 0
        elif num >= 100:
            # e.g. 1345 -> hour=13, minute=45 (standard FIRMS HHMM format)
            hour, minute = num // 100, num % 100
            if hour > 23: return raw  # not a valid HHMM value; bail out and return as-is
        else:
            # Numbers between 25-99 don't fit HHMM or a bare hour; treat as total minutes.
            hour, minute = num // 60, num % 60
            if hour > 23: return raw

        suffix = "AM" if hour < 12 else "PM"
        display_hour = 12 if hour % 12 == 0 else hour % 12
        return f"{display_hour}:{minute:02d} {suffix}"
    
    # If it wasn't a plain digit string, try to find an "HH:MM" pattern inside it.
    match = re.search(r"(\d{1,2})\s*:\s*(\d{2})", raw)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        suffix = "AM" if hour < 12 else "PM"
        display_hour = 12 if hour % 12 == 0 else hour % 12
        return f"{display_hour}:{minute:02d} {suffix}"

    # Nothing matched — return the original raw value unchanged.
    return raw


@st.cache_data(ttl=600, show_spinner=False)
def fetch_firms_data(map_key: str, source: str, area: str, day_range: int) -> pd.DataFrame:
    """
    Call the NASA FIRMS "area" CSV API and return the results as a DataFrame.

    Results are cached for 10 minutes (ttl=600) per unique combination of
    arguments, so repeated calls with the same settings won't re-hit the API.

    Raises:
        ValueError: if the HTTP request fails or the API responds with an
        "Invalid" key message.
    """
    map_key = str(map_key).strip()
    area = str(area).strip()
    url = f"{FIRMS_BASE_URL}/{map_key}/{source}/{area}/{day_range}"
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        raise ValueError(f"API Error {response.status_code}: {url}")
    text = response.text.strip()
    if "Invalid" in text[:100]:
        raise ValueError(f"Invalid Key: {text[:100]}")
        
    df = pd.read_csv(StringIO(text))
    
    # Normalize the acquisition date into DD-MM-YYYY strings and expose it
    # under a simpler "date" column used throughout the rest of the app.
    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.strftime("%d-%m-%Y")
        df["date"] = df["acq_date"]
    elif "date" not in df.columns:
        df["date"] = "N/A"
        
    # Normalize the acquisition time into a friendly AM/PM string, exposed
    # under a simpler "time" column.
    if "acq_time" in df.columns:
        df["acq_time"] = df["acq_time"].apply(format_time_ampm)
        df["time"] = df["acq_time"]
    elif "time" not in df.columns:
        df["time"] = ""

    return df


def frp_style(frp_val: float):
    """
    Map a Fire Radiative Power (FRP) value to a (color, marker_radius) pair
    used when plotting points on the map, so higher-intensity detections
    stand out visually (bigger + redder).
    """
    if pd.isna(frp_val): return "#888888", 3       # unknown/missing FRP -> grey, small
    if frp_val > 50: return "#ff3c3c", 7           # high intensity -> red, large
    elif frp_val > 10: return "#ffa552", 5         # medium intensity -> orange, medium
    return "#ffd93d", 3                            # low intensity -> yellow, small


# =================================================================
# PAGE: DASHBOARD
# =================================================================
if st.session_state.page == "Dashboard":
    # Three-column layout: left = configuration controls, center = map + metrics,
    # right = analytics tabs + live feed.
    c_left, c_center, c_right = st.columns([1, 2.5, 1])

    with c_left:
        # ---- Configuration panel ----
        st.markdown('<div class="config-box"><div class="config-title">Configuration</div>', unsafe_allow_html=True)

        # FIRMS MAP KEY: pre-filled from environment variable if available,
        # otherwise the user must type their own (masked as a password field).
        default_key = os.getenv("FIRMS_MAP_KEY", "")
        map_key = st.text_input("FIRMS MAP KEY", value=default_key, type="password", label_visibility="collapsed", placeholder="Enter MAP KEY").strip()

        st.markdown("**Satellite Selection**")
        st.session_state.source = st.selectbox("Source", SOURCES, index=0, label_visibility="collapsed")

        col_date, col_dn = st.columns(2)
        with col_date:
            st.markdown("**Date Range**")
            # How many days back (1-5) of detections to request from the API.
            day_range = st.slider("Days", min_value=1, max_value=5, value=5, label_visibility="collapsed")
            st.session_state.day_range = day_range
        with col_dn:
            st.markdown("**Day/Night**")
            # Filter detections by whether they occurred during day ('D') or night ('N') passes.
            selected_dn = st.multiselect("Day/Night", ['D', 'N'], default=['D', 'N'], label_visibility="collapsed")
            st.session_state.selected_dn = selected_dn

        st.markdown("**Region of Interest**")
        area_choice = st.selectbox("Area", list(PRESET_AREAS.keys()), index=0, label_visibility="collapsed")
        st.session_state.area_choice = area_choice
        if area_choice == "Custom (enter below)":
            # Let the user type a raw bounding box string: "min_lon,min_lat,max_lon,max_lat"
            area = st.text_input("BBox", value="68,6,97,37", label_visibility="collapsed")
        else:
            area = PRESET_AREAS[area_choice]

        st.markdown("**Confidence Level**")
        conf_labels = ["Low (0-30)", "Medium (30-70)", "High (70-100)"]
        # Client-side filter applied after fetching (FIRMS doesn't filter by confidence server-side here).
        selected_conf = st.multiselect("Confidence", conf_labels, default=conf_labels, label_visibility="collapsed")

        st.markdown("**Mission Status: <span style='color:#5fe08a;font-weight:900;'>Monitoring</span>**", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Opens the modal dialog that lets the user confirm/trigger a fresh data fetch.
        if st.button("🚀 Open Fetch Dialogue", use_container_width=True, type="primary"):
            open_fetch_dialog()

    with c_center:
        st.markdown('<div class="map-box">', unsafe_allow_html=True)
        
        # Can't call the API without a key — stop rendering the rest of the page.
        if not map_key:
            st.warning("👈 Enter your FIRMS MAP KEY.")
            st.stop()

        # Lazily fetch data into session_state the first time (or after it's
        # been cleared by the fetch dialog), so we don't re-fetch on every rerun.
        if "df" not in st.session_state: st.session_state.df = None

        if st.session_state.df is None:
            with st.spinner("Fetching FIRMS data..."):
                try:
                    st.session_state.df = fetch_firms_data(map_key, st.session_state.source, area, day_range)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.df = pd.DataFrame()

        df_raw = st.session_state.df
        # Work on a copy so filtering below doesn't mutate the cached/stored dataframe.
        df = df_raw.copy() if df_raw is not None and not df_raw.empty else pd.DataFrame()

        if len(df) > 0:
            # Bucket each row's numeric confidence into Low/Medium/High categories,
            # then apply the user's confidence filter (skip filtering if all 3 are selected).
            if "confidence" in df.columns:
                df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
                df["conf_cat"] = df["confidence"].apply(
                    lambda val: "Low (0-30)" if val < 30 else ("Medium (30-70)" if val < 70 else "High (70-100)")
                ).fillna("Unknown")
                if len(selected_conf) != 3:
                    df = df[df["conf_cat"].isin(selected_conf)]
            # Apply the day/night filter chosen in the sidebar.
            if "daynight" in df.columns:
                df = df[df["daynight"].isin(selected_dn)]

        if len(df) > 0:
            # Build a dark-themed Folium map centered on the mean lat/lon of the
            # filtered detections, then plot up to 2000 points (capped for performance)
            # as colored circle markers sized/colored by FRP intensity.
            fmap = folium.Map(location=[df["latitude"].mean(), df["longitude"].mean()], zoom_start=5, tiles="CartoDB dark_matter", control_scale=True)
            for _, row in df.head(2000).iterrows():
                frp_val = row.get("frp", 0)
                color, radius = frp_style(frp_val)
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=radius, color=color, weight=1,
                    fill=True, fill_color=color, fill_opacity=0.75,
                    popup=folium.Popup((f"<b>Date:</b> {row.get('date', 'N/A')} {row.get('time', '')}<br><b>FRP:</b> {row.get('frp', 'N/A')} MW"), max_width=300),
                ).add_to(fmap)
            # returned_objects=[] avoids sending map click/interaction data back to
            # Streamlit, since we don't need it (keeps reruns lighter).
            st_folium(fmap, width=None, height=500, returned_objects=[])
        else:
            st.info("No data after applying filters.")

        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Bottom summary metric cards ----
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            # Total number of detections currently shown (after filtering).
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Active Fires:</div><div class="metric-value">{len(df):,}</div></div>', unsafe_allow_html=True)
        with col_m2:
            # Sum of Fire Radiative Power across all filtered detections.
            total_frp = df["frp"].sum() if "frp" in df.columns else 0
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Total FRP (MW):</div><div class="metric-value">{total_frp:,.0f}</div></div>', unsafe_allow_html=True)
        with col_m3:
            # Percent change in detection count between the two most recent days present in the data.
            daily_change = "N/A"
            if "date" in df.columns:
                daily_counts = df.groupby("date").size().sort_index()
                if len(daily_counts) >= 2:
                    prev, latest = daily_counts.iloc[-2], daily_counts.iloc[-1]
                    if prev > 0: daily_change = f"{((latest - prev) / prev) * 100:+.1f}%"
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Daily Change:</div><div class="metric-value" style="font-size:2.2rem;color:#5fe08a;">{daily_change} ↑</div></div>', unsafe_allow_html=True)

    with c_right:
        # ---- Analytics tabs: Detections per Day / FRP Distribution ----
        st.markdown('<div class="side-panel"><div class="panel-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
        
        tab_daily, tab_frp = st.tabs(["📅 Detections per Day", "🔥 FRP Distribution"])
        
        with tab_daily:
            if len(df) > 0 and "date" in df.columns:
                # Count detections per calendar date and plot as a bar chart,
                # coloring bars along a gradient purely by their chronological index (idx).
                daily = df.groupby("date").size().reset_index(name="count").sort_values("date")
                daily['idx'] = range(len(daily))
                
                fig_daily = px.bar(daily, x='date', y='count', color='idx', color_continuous_scale=['#ff6b35', '#ff1493', '#9d00ff'])
                fig_daily.update_layout(
                    coloraxis_showscale=False,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=12),
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    xaxis=dict(showgrid=False, tickangle=-45),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False)
                )
                st.plotly_chart(fig_daily, use_container_width=True, config={'displayModeBar': False})
            else: st.caption("No Data")
            
        with tab_frp:
            if len(df) > 0 and "frp" in df.columns:
                # Bucket FRP values into fixed ranges and plot detection counts per bucket.
                frp_bins = pd.cut(df["frp"], bins=[0, 5, 10, 25, 50, 100, float("inf")], labels=["0-5", "5-10", "10-25", "25-50", "50-100", "100+"])
                bin_counts = frp_bins.value_counts().sort_index().reset_index()
                bin_counts.columns = ['FRP Range', 'Count']
                bin_counts['idx'] = range(len(bin_counts))
                
                fig_frp = px.bar(bin_counts, x='FRP Range', y='Count', color='idx', color_continuous_scale=['#ff6b35', '#ff1493', '#9d00ff'])
                fig_frp.update_layout(
                    coloraxis_showscale=False,
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', size=12),
                    margin=dict(l=0, r=0, t=10, b=0), height=300,
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False)
                )
                st.plotly_chart(fig_frp, use_container_width=True, config={'displayModeBar': False})
            else: st.caption("No Data")
            
        st.markdown('</div>', unsafe_allow_html=True)

        # ---- Live Data feed: most recent 12 detections, newest first ----
        st.markdown('<div class="side-panel"><div class="panel-title">Live Data</div>', unsafe_allow_html=True)
        if len(df) > 0:
            feed_rows = df.sort_values(by=["date", "time"], ascending=False).head(12)
            feed_html = '<div class="live-feed">'
            for _, row in feed_rows.iterrows():
                lat = row.get("latitude")
                lon = row.get("longitude")
                frp_v = row.get("frp", "N/A")
                time_v = row.get("time", "")
                feed_html += (f"Detections near: <b>{lat:.2f}°N, {lon:.2f}°E</b>, FRP: {frp_v}, {time_v}<br>")
            feed_html += "</div>"
            st.markdown(feed_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# =================================================================
# PAGE: DATA ARCHIVES
# =================================================================
elif st.session_state.page == "Data Archives":
    st.title("📋 Data Archives")
    # Independent of the Dashboard page's cached df — this page always
    # fetches a fresh worldwide, 3-day window using the first source in SOURCES.
    default_key = os.getenv("FIRMS_MAP_KEY", "")
    map_key = default_key if default_key else st.text_input("Enter MAP KEY:")
    if map_key:
        try:
            df = fetch_firms_data(map_key.strip(), SOURCES[0], "world", 3)
            st.dataframe(df, use_container_width=True, height=500)
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Enter MAP KEY.")

# =================================================================
# PAGE: ANALYSIS TOOLS
# =================================================================
elif st.session_state.page == "Analysis Tools":
    st.title("📈 Analysis Tools")

    # This page reuses whatever data was already loaded on the Dashboard page,
    # rather than fetching its own — so it requires the user to visit Dashboard first.
    if "df" not in st.session_state or st.session_state.df is None or st.session_state.df.empty:
        st.warning("⚠️ Please load data first using the **Dashboard** page.")
        st.info("Go to the Dashboard, enter your FIRMS MAP KEY, and click 'Fetch Latest Data', then come back here.")
    else:
        df = st.session_state.df
        st.success(f"🔬 Currently analyzing {len(df)} detections.")
        if st.button("🔄 Clear Data for New Analysis", use_container_width=True):
            st.session_state.df = None
            st.rerun()

        # ---- Summary metrics row ----
        st.markdown("### 📊 Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Points", f"{len(df):,}")
        df["frp"] = pd.to_numeric(df["frp"], errors="coerce")
        col2.metric("Avg FRP", f"{df['frp'].mean():.2f} MW")
        col3.metric("Max FRP", f"{df['frp'].max():.2f} MW")
        
        if "date" in df.columns:
            col4.metric("Date Range", f"{df['date'].min()} to {df['date'].max()}")
        else:
            col4.metric("Date Range", "N/A")

        # ---- FRP vs Confidence line chart ----
        st.markdown("### 🎯 FRP vs Confidence Line Graph")
        if "confidence" in df.columns:
            def parse_conf(val):
                """
                Convert a confidence value to a numeric scale.
                MODIS data uses letter codes ('l'/'n'/'h' = low/nominal/high),
                while VIIRS data typically already uses a 0-100 numeric scale.
                Returns None if the value can't be interpreted either way.
                """
                val = str(val).strip().lower()
                if val == 'l': return 30
                if val == 'n': return 60
                if val == 'h': return 100
                try: return float(val)
                except: return None
            df["confidence"] = df["confidence"].apply(parse_conf)
            chart_data = df[["frp", "confidence"]].dropna()
            if not chart_data.empty:
                chart_data = chart_data.sort_values(by="confidence")
                fig_line = px.line(chart_data, x="confidence", y="frp", markers=True, color_discrete_sequence=['#ff6b35'], labels={"frp": "FRP (MW)", "confidence": "Confidence"})
                fig_line.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white', size=14), margin=dict(l=0, r=0, t=30, b=0), height=400, xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', zeroline=False))
                st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("No valid FRP/Confidence data points for line graph.")
        else:
            st.caption("Confidence column not found.")

        # ---- Hourly detection trend ----
        st.markdown("### ⏰ Detections Over Time (Hourly Trend)")
        if "time" in df.columns:
            def extract_hour(time_str):
                """
                Pull a 24-hour integer hour out of a formatted "H:MM AM/PM"
                time string (as produced by format_time_ampm). Returns None
                if no hour pattern is found.
                """
                if pd.isna(time_str): return None
                match = re.search(r"(\d{1,2}):", str(time_str))
                if match:
                    hour = int(match.group(1))
                    if "PM" in str(time_str) and hour != 12: hour += 12
                    if "AM" in str(time_str) and hour == 12: hour = 0
                    return hour
                return None
            df["hour"] = df["time"].apply(extract_hour)
            hourly_counts = df.groupby("hour").size().reset_index(name="Count").dropna()
            if not hourly_counts.empty:
                fig_hourly = px.bar(hourly_counts, x="hour", y="Count", color_discrete_sequence=['#ffa552'])
                fig_hourly.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white', size=14), margin=dict(l=0, r=0, t=10, b=0), height=300)
                st.plotly_chart(fig_hourly, use_container_width=True, config={'displayModeBar': False})
            else:
                st.caption("No valid time data.")
        else:
            st.caption("Time column not found.")

# =================================================================
# PAGE: ALERTS
# =================================================================
elif st.session_state.page == "Alerts":
    st.title("🚨 Alerts")
    # Like Data Archives, this page fetches its own fresh worldwide, 3-day
    # window (using whichever source is currently selected) rather than
    # reusing the Dashboard's stored dataframe.
    default_key = os.getenv("FIRMS_MAP_KEY", "")
    map_key = default_key if default_key else st.text_input("Enter MAP KEY:")
    if map_key:
        try:
            df = fetch_firms_data(map_key.strip(), st.session_state.source, "world", 3)
            if len(df) > 0 and "frp" in df.columns:
                # Show the top 10 highest-intensity detections globally.
                top_alerts = df.sort_values("frp", ascending=False).head(10)
                for _, row in top_alerts.iterrows():
                    st.markdown(f"<div class='side-panel'><b>🔥 FRP:</b> {row.get('frp', 'N/A')} MW at {row['latitude']:.2f}, {row['longitude']:.2f} on {row.get('date', 'N/A')} at {row.get('time', '')}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Enter MAP KEY.")

# =================================================================
# PAGE: ABOUT
# =================================================================
elif st.session_state.page == "About":
    st.title("🌍 THERMOWATCH Dashboard")
    
    # Static informational content about the project, features, tech stack,
    # target users, and a disclaimer about data accuracy.
    st.markdown("""
    ## 📖 About the Project
    Welcome to the **THERMOWATCH Dashboard**, a robust, near-real-time web application designed to monitor and visualize active fire and thermal anomalies across the globe. 
    
    Built to make complex satellite data accessible, this dashboard empowers researchers, environmentalists, and disaster management teams to detect hotspots quickly and make informed decisions.

    ---
    
    ### ✨ Key Features
    
    - **🗺️ Interactive Dashboard:** A dynamic, dark-themed map with satellite layers, dynamic heat markers, and advanced filtering by Satellite Source, Date Range, Day/Night, and Confidence Level.
    - **📋 Data Archives:** Direct access to downloadable raw data (CSV) for offline analysis and record-keeping.
    - **📈 Advanced Analysis Tools:** Comprehensive graphs including FRP vs. Confidence line charts, Detections per Day, FRP Distribution, and Hourly Trends.
    - **🚨 Live Alerts:** Automatically surfaces the highest-intensity thermal events with precise location coordinates and FRP values.
    - **🚀 Fetch Dialogue Box:** A seamless, centralized popup to refresh data quickly without navigating away.
    
    ---
    
    ### 🛠️ Technology Stack
    
    - **Frontend:** Streamlit (Python) for rapid, interactive UI development.
    - **Mapping & Visualization:** Folium & Leaflet for interactive maps, Plotly for dynamic graphs.
    - **Data Processing:** Pandas for real-time data cleaning and manipulation.
    - **Data Source:** [NASA FIRMS API](https://firms.modaps.eosdis.nasa.gov/) (Fire Information for Resource Management System) providing VIIRS and MODIS satellite data.
    
    ---
    
    ### 🎯 Who is this for?
    
    - **Wildlife & Forest Departments:** Tracking potential fire outbreaks in real-time.
    - **Environmental Scientists:** Studying thermal activity and atmospheric anomalies.
    - **Agricultural Analysts:** Monitoring crop residue burning or farm fires.
    - **Emergency Response Teams:** Identifying precise coordinates for active wildfire management.
    
    ---
    
    ### ⚠️ Disclaimer
    This application uses near-real-time satellite data. Please note that data availability, refresh rates, and detection accuracy may vary based on satellite pass timings and atmospheric conditions. Always cross-reference critical data with official local sources.
    
    **Powered by Streamlit & NASA FIRMS.**
    """)

# Footer bar shown on every page except "About" (which has its own closing content).
if st.session_state.page != "About":
    st.markdown('<div class="footer"><span>NASA FIRMS | THERMOWATCH | v2.0</span><span>Privacy Policy | Terms of Use | Contact</span></div>', unsafe_allow_html=True)