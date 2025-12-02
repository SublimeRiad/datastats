import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. Page Config & CSS for Dense Layout ---
st.set_page_config(page_title="BSP Monitoring", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS to reduce padding and make it look like a dashboard screen
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        h1 { font-size: 1.8rem !important; margin-bottom: 0 !important;}
        .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. Database Connection ---
def init_connection():
    try:
        return mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
        return None

# --- 3. Data Functions ---

@st.cache_data(ttl=300) # Cache data for 5 minutes to improve performance
def get_global_data():
    conn = init_connection()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    
    # Query 1: Timeline by Location
    query_timeline = """
    SELECT ns.date_log, l.name as location_name, SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM glpi_network_stats ns
    JOIN glpi_computers c ON ns.computers_id = c.id
    JOIN glpi_locations l ON c.locations_id = l.id
    WHERE ns.app_name LIKE '%bsp.exe%'
    GROUP BY ns.date_log, l.name
    ORDER BY ns.date_log ASC;
    """
    
    # Query 2: Ranking by Location
    query_ranking = """
    SELECT l.name as location_name, SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM glpi_network_stats ns
    JOIN glpi_computers c ON ns.computers_id = c.id
    JOIN glpi_locations l ON c.locations_id = l.id
    WHERE ns.app_name LIKE '%bsp.exe%'
    GROUP BY l.name
    ORDER BY total_bytes DESC;
    """
    
    try:
        df_time = pd.read_sql(query_timeline, conn)
        df_rank = pd.read_sql(query_ranking, conn)
        conn.close()
        return df_time, df_rank
    except Exception:
        conn.close()
        return pd.DataFrame(), pd.DataFrame()

def get_player_data(player_id):
    conn = init_connection()
    if conn is None: return pd.DataFrame()
    query = """
    SELECT ns.date_log, l.name as location_name, a.tag as player_id,
    SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM glpi_network_stats ns
    JOIN glpi_computers c ON ns.computers_id = c.id
    JOIN glpi_locations l ON c.locations_id = l.id
    JOIN glpi_agents a ON a.items_id = c.id AND a.itemtype = 'Computer'
    WHERE ns.app_name LIKE '%bsp.exe%' AND a.tag LIKE %s
    GROUP BY ns.date_log, l.name, a.tag ORDER BY ns.date_log ASC;
    """
    try:
        df = pd.read_sql(query, conn, params=(f"%{player_id}%",))
        conn.close()
        return df
    except Exception:
        conn.close()
        return pd.DataFrame()

# --- 4. Main Execution ---

# Header
st.title("📊 BSP.exe Network Monitoring")

# Load Data
df_timeline, df_ranking = get_global_data()

if not df_timeline.empty and not df_ranking.empty:
    # Process Data
    df_timeline['total_mb'] = (df_timeline['total_bytes'] / (1024 * 1024)).round(2)
    df_ranking['total_mb'] = (df_ranking['total_bytes'] / (1024 * 1024)).round(2)
    
    total_consumed = df_ranking['total_mb'].sum()
    top_location = df_ranking.iloc[0]['location_name']
    top_val = df_ranking.iloc[0]['total_mb']

    # --- Row 1: KPI Metrics ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Data (Period)", f"{total_consumed:,.0f} MB")
    kpi2.metric("Top Location", f"{top_location}", f"{top_val:.0f} MB")
    kpi3.metric("Locations Active", f"{df_ranking['location_name'].nunique()}")
    kpi4.metric("Last Date Logged", str(df_timeline['date_log'].max()))

    # --- Row 2: Main Charts (Side by Side) ---
    col_left, col_right = st.columns([2, 1]) # Left chart is wider (2/3)

    with col_left:
        st.caption("📈 Daily Consumption by Location (Timeline)")
        fig_time = px.line(
            df_timeline, x='date_log', y='total_mb', color='location_name',
            labels={'total_mb': 'MB', 'date_log': ''},
            height=350 # Fixed height for density
        )
        fig_time.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig_time, use_container_width=True)

    with col_right:
        st.caption("🏆 Top Consumers by Location")
        fig_rank = px.bar(
            df_ranking.head(10), x='total_mb', y='location_name', orientation='h',
            color='total_mb', color_continuous_scale='Teal',
            labels={'total_mb': 'MB', 'location_name': ''},
            height=350
        )
        fig_rank.update_layout(margin=dict(l=10, r=10, t=10, b=10), yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_rank, use_container_width=True)

else:
    st.warning("No data available in database.")

# --- 5. Sidebar: Search Tool (Hidden by default) ---
with st.sidebar:
    st.header("🔎 Player Analysis")
    st.write("Use this tool to inspect specific players.")
    player_input = st.text_input("Enter Player Tag", "")
    
    if player_input:
        df_p = get_player_data(player_input)
        if not df_p.empty:
            df_p['total_mb'] = (df_p['total_bytes'] / (1024 * 1024)).round(2)
            st.success(f"Found: {player_input}")
            st.metric("Total", f"{df_p['total_mb'].sum():.2f} MB")
            fig_p = px.area(df_p, x='date_log', y='total_mb', title="Player Usage")
            fig_p.update_layout(margin=dict(l=0,r=0,t=30,b=0), height=200)
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.error("No data found.")
