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

# 1. Function: Global Stats by Location (Bar Chart)
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

# 2. Function: Global Timeline (Total consumption per day)
def get_global_timeline():
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        ns.date_log,
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM 
        glpi_network_stats ns
    WHERE 
        ns.app_name LIKE '%bsp.exe%'
    GROUP BY 
        ns.date_log
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

st.title("📊 DATA CONSUMPTION DASHBOARD - BROADSIGN")

# Load data
with st.spinner('Loading statistics...'):
    df_timeline = get_global_timeline()
    df_location = get_global_stats_by_location()

# Convert bytes to MB
if not df_timeline.empty:
    df_timeline['total_mb'] = (df_timeline['total_bytes'] / (1024 * 1024)).round(2)
if not df_location.empty:
    df_location['total_mb'] = (df_location['total_bytes'] / (1024 * 1024)).round(2)
    # Convertir les noms de lieux en MAJUSCULES pour l'affichage
    df_location['location_name'] = df_location['location_name'].str.upper()

# Display Global Metrics at the top
if not df_timeline.empty:
    col_metric1, col_metric2 = st.columns(2)
    col_metric1.metric("TOTAL CONSUMPTION (ALL TIME)", f"{df_timeline['total_mb'].sum():.2f} MB")
    col_metric2.metric("PEAK DAILY CONSUMPTION", f"{df_timeline['total_mb'].max():.2f} MB")

st.markdown("---")

# Main Graphs Layout (Side by Side)
if not df_timeline.empty and not df_location.empty:
    col1, col2 = st.columns(2) # Creates 2 equal columns

    # Left Column: Timeline
    with col1:
        st.subheader("📈 GLOBAL TIMELINE")
        fig_timeline = px.area(
            df_timeline,
            x='date_log',
            y='total_mb',
            title="EVOLUTION OF DATA USAGE",
            labels={'total_mb': 'Consumption (MB)', 'date_log': 'Date'},
            markers=True
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # Right Column: Location Ranking
    with col2:
        st.subheader("🏢 RANKING BY LOCATION")
        fig_global = px.bar(
            df_location, 
            x='location_name', 
            y='total_mb',
            color='total_mb',
            title="CONSUMPTION PER LOCATION",
            labels={'total_mb': 'Total (MB)', 'location_name': 'Location'},
            color_continuous_scale='Viridis'
        )
        fig_global.update_layout(xaxis_tickangle=-45) 
        st.plotly_chart(fig_global, use_container_width=True)

    # Raw data expander at the bottom (Expanded & Renamed)
    # Préparation du DataFrame pour l'affichage (Renommage des colonnes)
    df_display = df_location[['location_name', 'total_mb']].rename(
        columns={
            'location_name': 'LOCATION', 
            'total_mb': 'TOTAL MB'
        }
    )
    
    with st.expander("VIEW RAW DATA BY LOCATION", expanded=True):
        st.dataframe(
            df_display, 
            use_container_width=True,
            hide_index=True # Masque la colonne d'index (0, 1, 2...) pour un look plus propre
        )

elif df_timeline.empty and df_location.empty:
    st.info("No data available.")
