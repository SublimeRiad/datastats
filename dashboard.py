import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Load security variables
load_dotenv()

# Page Configuration
st.set_page_config(page_title="BSP.exe Dashboard", layout="wide")

# Database Connection Function
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
        st.error(f"Database connection error: {e}")
        return None

# 1. Function: Detailed data per Player ID (Search)
def get_player_data(player_id):
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        ns.date_log,
        l.name as location_name,
        a.tag as player_id,
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM 
        glpi_network_stats ns
    JOIN 
        glpi_computers c ON ns.computers_id = c.id
    JOIN 
        glpi_locations l ON c.locations_id = l.id
    JOIN 
        glpi_agents a ON a.items_id = c.id AND a.itemtype = 'Computer'
    WHERE 
        ns.app_name LIKE '%bsp.exe%'
        AND a.tag LIKE %s
    GROUP BY 
        ns.date_log, l.name, a.tag
    ORDER BY 
        ns.date_log ASC;
    """
    try:
        df = pd.read_sql(query, conn, params=(f"%{player_id}%",))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Player query error: {e}")
        conn.close()
        return pd.DataFrame()

# 2. Function: Global Stats by Location (Bar Chart)
def get_global_stats_by_location():
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        l.name as location_name,
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM 
        glpi_network_stats ns
    JOIN 
        glpi_computers c ON ns.computers_id = c.id
    JOIN 
        glpi_locations l ON c.locations_id = l.id
    WHERE 
        ns.app_name LIKE '%bsp.exe%'
    GROUP BY 
        l.name
    ORDER BY 
        total_bytes DESC;
    """
    try:
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Global stats query error: {e}")
        conn.close()
        return pd.DataFrame()

# 3. Function: Global Timeline by Location (Multi-line Chart)
def get_global_timeline_by_location():
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        ns.date_log,
        l.name as location_name,
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM 
        glpi_network_stats ns
    JOIN 
        glpi_computers c ON ns.computers_id = c.id
    JOIN 
        glpi_locations l ON c.locations_id = l.id
    WHERE 
        ns.app_name LIKE '%bsp.exe%'
    GROUP BY 
        ns.date_log, l.name
    ORDER BY 
        ns.date_log ASC;
    """
    try:
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Global timeline query error: {e}")
        conn.close()
        return pd.DataFrame()

# --- User Interface ---

st.title("📊 Data Consumption Dashboard - Broadsign")

# --- Section 1: Search ---
st.subheader("🔎 Search by Player ID")
col1, col2 = st.columns([1, 3])
with col1:
    player_id_input = st.text_input("Enter a Tag (e.g., DAL-DDP...)", "")

if player_id_input:
    with st.spinner(f'Loading data for {player_id_input}...'):
        df_player = get_player_data(player_id_input)

    if not df_player.empty:
        df_player['total_mb'] = (df_player['total_bytes'] / (1024 * 1024)).round(2)
        st.success(f"Data found for: {player_id_input}")
        st.metric("Total Consumed (This tag)", f"{df_player['total_mb'].sum():.2f} MB")
        
        fig_player = px.line(
            df_player, 
            x='date_log', 
            y='total_mb', 
            color='location_name',
            markers=True,
            title=f"Daily consumption for: {player_id_input}",
            labels={'total_mb': 'Consumption (MB)', 'date_log': 'Date'}
        )
        st.plotly_chart(fig_player, use_container_width=True)
    else:
        st.warning("No data found for this Player ID.")

st.divider() 

# --- Section 2: Global Overview ---
st.subheader("🌍 Global Network Overview")

# Load global data
with st.spinner('Loading global statistics...'):
    df_timeline = get_global_timeline_by_location()
    df_location = get_global_stats_by_location()

# Convert bytes to MB
if not df_timeline.empty:
    df_timeline['total_mb'] = (df_timeline['total_bytes'] / (1024 * 1024)).round(2)
if not df_location.empty:
    df_location['total_mb'] = (df_location['total_bytes'] / (1024 * 1024)).round(2)

# Display Global Metrics
if not df_timeline.empty:
    col_metric1, col_metric2 = st.columns(2)
    col_metric1.metric("Total Consumption (All time)", f"{df_timeline['total_mb'].sum():.2f} MB")
    col_metric2.metric("Peak Daily Consumption", f"{df_timeline['total_mb'].max():.2f} MB")

# Graph 1: Global Timeline by Location
if not df_timeline.empty:
    st.markdown("### 📈 Evolution of Data Usage by Location")
    fig_timeline = px.line(
        df_timeline,
        x='date_log',
        y='total_mb',
        color='location_name', # Splits lines by location
        title="Daily Consumption per Location (bsp.exe)",
        labels={'total_mb': 'Consumption (MB)', 'date_log': 'Date', 'location_name': 'Location'},
        markers=True
    )
    # Interactive tooltips
    fig_timeline.update_traces(mode="lines+markers")
    fig_timeline.update_layout(hovermode="x unified")
    
    st.plotly_chart(fig_timeline, use_container_width=True)

# Graph 2: Location Ranking
if not df_location.empty:
    st.markdown("### 🏢 Consumption Ranking by Location")
    fig_global = px.bar(
        df_location, 
        x='location_name', 
        y='total_mb',
        color='total_mb',
        title="Total Data Consumption per Location",
        labels={'total_mb': 'Total Consumed (MB)', 'location_name': 'Location'},
        color_continuous_scale='Viridis'
    )
    fig_global.update_layout(xaxis_tickangle=-45) 
    st.plotly_chart(fig_global, use_container_width=True)
    
    with st.expander("View raw data by location"):
        st.dataframe(df_location[['location_name', 'total_mb']])
else:
    st.info("No global data available.")
