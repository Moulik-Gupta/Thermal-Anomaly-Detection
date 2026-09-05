"""
NASA FIRMS Thermal Detection Dashboard - V39 (Hide Deploy, Keep Three Dots)
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

load_dotenv()

st.set_page_config(
    page_title="FIRMS Thermal Detection Dashboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

SOURCES = [
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
]

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
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    ext = image_path.split(".")[-1].lower()
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    return f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(5,5,15,0.45), rgba(5,5,15,0.72)), url("data:image/{mime};base64,{encoded}");
            background-size: cover; background-position: center; background-attachment: fixed;
        }}
        </style>
        """

BACKGROUND_IMAGE_PATH = "assets/space-bg.jpg"
bg_css = get_background_css(BACKGROUND_IMAGE_PATH)
if bg_css:
    st.markdown(bg_css, unsafe_allow_html=True)

# ---------------------------------------------------------------
# HIDE DEPLOY BUTTON (BUT KEEP THE THREE DOTS)
# ---------------------------------------------------------------
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
    setTimeout(hideDeployButton, 300);
    setInterval(hideDeployButton, 2000);
    </script>
    """,
    height=0,
    scrolling=False,
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0a0e1f;
        background-image: radial-gradient(180deg, #0a0e1f 0%, #0d1024 60%, #120a1e 100%);
        background-attachment: fixed;
        color: #ffffff;
    }
    
    .sticky-nav {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        z-index: 999999 !important;
        background-color: rgba(10, 12, 24, 0.95) !important;
        backdrop-filter: blur(15px) !important;
        border-bottom: 2px solid rgba(255, 107, 53, 0.8) !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.8) !important;
    }
    
    .main .block-container { 
        padding-top: 7rem !important;
        max-width: 1600px !important; 
    }

    html, body, [class*="css"], p, span, label, h1, h2, h3, h4, h5, h6, strong, b {
        font-size: 1.05rem !important; 
        font-weight: 700 !important;
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px #000000 !important;
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div {
        font-size: 1rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }

    div.stButton > button {
        font-size: 1rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        white-space: nowrap !important;
    }
    div.stButton > button:hover { color: #ff6b35 !important; }
    .navbar-left { font-size: 1.8rem !important; font-weight: 900; color: #ff6b35; text-shadow: 0 0 10px rgba(255,107,53,0.8); }

    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1rem !important;
        font-weight: 800 !important;
        color: #FF9466 !important;
    }

    .config-box { background: rgba(10,12,24,0.85); border: 2px solid rgba(255,107,53,0.4); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .config-title { font-size: 1.3rem !important; margin-bottom: 15px; color: #ffffff; }
    
    .bottom-metric-box { background: rgba(10,12,24,0.85); border: 2px solid rgba(255,107,53,0.35); border-radius: 12px; padding: 15px; text-align: center; color: white; margin-top: 10px; box-shadow: 0 8px 15px rgba(0,0,0,0.6); }
    .metric-label { font-size: 1rem !important; color: #ff9466; font-weight: 800 !important; }
    .metric-value { font-size: 2.5rem !important; font-weight: 900 !important; color: #ffffff !important; text-shadow: 2px 2px 4px #000000 !important; }
    
    .side-panel { background: rgba(10,12,24,0.85); border: 2px solid rgba(255,107,53,0.35); border-radius: 12px; padding: 15px; margin-bottom: 15px; }
    .panel-title { font-size: 1.3rem !important; font-weight: 900; color: #ffffff; border-bottom: 2px solid rgba(255,107,53,0.4); padding-bottom: 8px; text-shadow: 1px 1px 3px #000000; }
    
    .stTabs [data-baseweb="tab"] { font-size: 1.1rem !important; font-weight: 800 !important; }
    
    .live-feed { max-height: 250px; overflow-y: auto; font-size: 0.9rem !important; color: #ffffff !important; line-height: 1.9; font-weight: 800 !important; text-shadow: 1px 1px 2px #000000; }
    .live-feed b { color: #ffd93d !important; }
    
    .footer { margin-top: 30px; border-top: 2px solid rgba(255,107,53,0.4); padding-top: 10px; font-size: 0.9rem !important; color: #FFFFFF !important; font-weight: 800 !important; text-shadow: 1px 1px 2px #000000; }
    
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

if "page" not in st.session_state: st.session_state.page = "Dashboard"
if "source" not in st.session_state: st.session_state.source = SOURCES[0]

@st.dialog("🚀 Fetch Data Options")
def open_fetch_dialog():
    st.write("Review your current settings and fetch fresh thermal data:")
    st.markdown(f"**🛰️ Satellite:** {st.session_state.source}")
    st.markdown(f"**📅 Day Range:** {st.session_state.get('day_range', 5)} days")
    area_choice = st.session_state.get('area_choice', "India")
    st.markdown(f"**🌍 Region:** {area_choice}")
    selected_dn = st.session_state.get('selected_dn', ['D', 'N'])
    st.markdown(f"**🌗 Day/Night:** {', '.join(selected_dn)}")
    st.divider()
    
    if st.button("⬇️ Fetch Latest Data", use_container_width=True, type="primary"):
        fetch_firms_data.clear()
        st.session_state.df = None
        st.rerun()
    
    if st.button("Cancel", use_container_width=True):
        st.rerun()

# ---------------------------------------------------------------
# FIXED NAVBAR
# ---------------------------------------------------------------
with st.container():
    st.markdown('<div class="sticky-nav">', unsafe_allow_html=True)
    col_logo, col_spacer, col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns([2.5, 2, 1, 1, 1, 1, 1])
    with col_logo:
        st.markdown('<div class="navbar-left">🔥 Thermal Intelligence</div>', unsafe_allow_html=True)
    with col_spacer:
        pass
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
    if pd.isna(value): return ""
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none"}: return ""
    if raw.endswith('.0'): raw = raw[:-2]
    
    if raw.isdigit():
        num = int(raw)
        if 0 <= num <= 24: hour, minute = num, 0
        elif num >= 100:
            hour, minute = num // 100, num % 100
            if hour > 23: return raw
        else:
            hour, minute = num // 60, num % 60
            if hour > 23: return raw

        suffix = "AM" if hour < 12 else "PM"
        display_hour = 12 if hour % 12 == 0 else hour % 12
        return f"{display_hour}:{minute:02d} {suffix}"
    
    match = re.search(r"(\d{1,2})\s*:\s*(\d{2})", raw)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        suffix = "AM" if hour < 12 else "PM"
        display_hour = 12 if hour % 12 == 0 else hour % 12
        return f"{display_hour}:{minute:02d} {suffix}"

    return raw

@st.cache_data(ttl=600, show_spinner=False)
def fetch_firms_data(map_key: str, source: str, area: str, day_range: int) -> pd.DataFrame:
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
    
    if "acq_date" in df.columns:
        df["acq_date"] = pd.to_datetime(df["acq_date"], errors="coerce").dt.strftime("%d-%m-%Y")
        df["date"] = df["acq_date"]
    elif "date" not in df.columns:
        df["date"] = "N/A"
        
    if "acq_time" in df.columns:
        df["acq_time"] = df["acq_time"].apply(format_time_ampm)
        df["time"] = df["acq_time"]
    elif "time" not in df.columns:
        df["time"] = ""

    return df

def frp_style(frp_val: float):
    if pd.isna(frp_val): return "#888888", 3
    if frp_val > 50: return "#ff3c3c", 7
    elif frp_val > 10: return "#ffa552", 5
    return "#ffd93d", 3

if st.session_state.page == "Dashboard":
    c_left, c_center, c_right = st.columns([1, 2.5, 1])

    with c_left:
        st.markdown('<div class="config-box"><div class="config-title">Configuration</div>', unsafe_allow_html=True)
        default_key = os.getenv("FIRMS_MAP_KEY", "")
        map_key = st.text_input("FIRMS MAP KEY", value=default_key, type="password", label_visibility="collapsed", placeholder="Enter MAP KEY").strip()

        st.markdown("**Satellite Selection**")
        st.session_state.source = st.selectbox("Source", SOURCES, index=0, label_visibility="collapsed")

        col_date, col_dn = st.columns(2)
        with col_date:
            st.markdown("**Date Range**")
            day_range = st.slider("Days", min_value=1, max_value=10, value=5, label_visibility="collapsed")
            st.session_state.day_range = day_range
        with col_dn:
            st.markdown("**Day/Night**")
            selected_dn = st.multiselect("Day/Night", ['D', 'N'], default=['D', 'N'], label_visibility="collapsed")
            st.session_state.selected_dn = selected_dn

        st.markdown("**Region of Interest**")
        area_choice = st.selectbox("Area", list(PRESET_AREAS.keys()), index=0, label_visibility="collapsed")
        st.session_state.area_choice = area_choice
        if area_choice == "Custom (enter below)":
            area = st.text_input("BBox", value="68,6,97,37", label_visibility="collapsed")
        else:
            area = PRESET_AREAS[area_choice]

        st.markdown("**Confidence Level**")
        conf_labels = ["Low (0-30)", "Medium (30-70)", "High (70-100)"]
        selected_conf = st.multiselect("Confidence", conf_labels, default=conf_labels, label_visibility="collapsed")

        st.markdown("**Mission Status: <span style='color:#5fe08a;font-weight:900;'>Monitoring</span>**", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("🚀 Open Fetch Dialogue", use_container_width=True, type="primary"):
            open_fetch_dialog()

    with c_center:
        st.markdown('<div class="map-box">', unsafe_allow_html=True)
        
        if not map_key:
            st.warning("👈 Enter your FIRMS MAP KEY.")
            st.stop()

        if "df" not in st.session_state: st.session_state.df = None

        if st.session_state.df is None:
            with st.spinner("Fetching FIRMS data..."):
                try:
                    st.session_state.df = fetch_firms_data(map_key, st.session_state.source, area, day_range)
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.session_state.df = pd.DataFrame()

        df_raw = st.session_state.df
        df = df_raw.copy() if df_raw is not None and not df_raw.empty else pd.DataFrame()

        if len(df) > 0:
            if "confidence" in df.columns:
                df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce")
                df["conf_cat"] = df["confidence"].apply(
                    lambda val: "Low (0-30)" if val < 30 else ("Medium (30-70)" if val < 70 else "High (70-100)")
                ).fillna("Unknown")
                if len(selected_conf) != 3:
                    df = df[df["conf_cat"].isin(selected_conf)]
            if "daynight" in df.columns:
                df = df[df["daynight"].isin(selected_dn)]

        if len(df) > 0:
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
            st_folium(fmap, width=None, height=500, returned_objects=[])
        else:
            st.info("No data after applying filters.")

        st.markdown('</div>', unsafe_allow_html=True)

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Active Fires:</div><div class="metric-value">{len(df):,}</div></div>', unsafe_allow_html=True)
        with col_m2:
            total_frp = df["frp"].sum() if "frp" in df.columns else 0
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Total FRP (MW):</div><div class="metric-value">{total_frp:,.0f}</div></div>', unsafe_allow_html=True)
        with col_m3:
            daily_change = "N/A"
            if "date" in df.columns:
                daily_counts = df.groupby("date").size().sort_index()
                if len(daily_counts) >= 2:
                    prev, latest = daily_counts.iloc[-2], daily_counts.iloc[-1]
                    if prev > 0: daily_change = f"{((latest - prev) / prev) * 100:+.1f}%"
            st.markdown(f'<div class="bottom-metric-box"><div class="metric-label">Daily Change:</div><div class="metric-value" style="font-size:2.2rem;color:#5fe08a;">{daily_change} ↑</div></div>', unsafe_allow_html=True)

    with c_right:
        st.markdown('<div class="side-panel"><div class="panel-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
        
        tab_daily, tab_frp = st.tabs(["📅 Detections per Day", "🔥 FRP Distribution"])
        
        with tab_daily:
            if len(df) > 0 and "date" in df.columns:
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

elif st.session_state.page == "Data Archives":
    st.title("📋 Data Archives")
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

elif st.session_state.page == "Analysis Tools":
    st.title("📈 Analysis Tools")

    if "df" not in st.session_state or st.session_state.df is None or st.session_state.df.empty:
        st.warning("⚠️ Please load data first using the **Dashboard** page.")
        st.info("Go to the Dashboard, enter your FIRMS MAP KEY, and click 'Fetch Latest Data', then come back here.")
    else:
        df = st.session_state.df
        st.success(f"🔬 Currently analyzing {len(df)} detections.")
        if st.button("🔄 Clear Data for New Analysis", use_container_width=True):
            st.session_state.df = None
            st.rerun()

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

        st.markdown("### 🎯 FRP vs Confidence Line Graph")
        if "confidence" in df.columns:
            def parse_conf(val):
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

        st.markdown("### ⏰ Detections Over Time (Hourly Trend)")
        if "time" in df.columns:
            def extract_hour(time_str):
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

elif st.session_state.page == "Alerts":
    st.title("🚨 Alerts")
    default_key = os.getenv("FIRMS_MAP_KEY", "")
    map_key = default_key if default_key else st.text_input("Enter MAP KEY:")
    if map_key:
        try:
            df = fetch_firms_data(map_key.strip(), st.session_state.source, "world", 3)
            if len(df) > 0 and "frp" in df.columns:
                top_alerts = df.sort_values("frp", ascending=False).head(10)
                for _, row in top_alerts.iterrows():
                    st.markdown(f"<div class='side-panel'><b>🔥 FRP:</b> {row.get('frp', 'N/A')} MW at {row['latitude']:.2f}, {row['longitude']:.2f} on {row.get('date', 'N/A')} at {row.get('time', '')}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Enter MAP KEY.")

elif st.session_state.page == "About":
    st.title("🌍 Thermal Intelligence Dashboard")
    
    st.markdown("""
    ## 📖 About the Project
    Welcome to the **Thermal Intelligence Dashboard**, a robust, near-real-time web application designed to monitor and visualize active fire and thermal anomalies across the globe. 
    
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

if st.session_state.page != "About":
    st.markdown('<div class="footer"><span>NASA FIRMS | Thermal Intelligence | v2.0</span><span>Privacy Policy | Terms of Use | Contact</span></div>', unsafe_allow_html=True)