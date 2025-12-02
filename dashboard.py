import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Load security variables from .env file (or Secrets on Streamlit Cloud)
load_dotenv()

# Page Configuration
st.set_page_config(page_title="BSP.exe Consumption", layout="wide")

# Function to connect to the database
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

# Function to retrieve data
def get_data(player_id):
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()

    # The SQL query joins the 4 necessary tables
    # Filters by 'bsp.exe' and the TAG (Player ID)
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
        # Using pandas to read directly into a DataFrame
        # %s is replaced by player_id securely
        df = pd.read_sql(query, conn, params=(f"%{player_id}%",))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        conn.close()
        return pd.DataFrame()

# --- User Interface ---

st.title("📊 Data Consumption Analysis - bsp.exe")
st.markdown("Visualization of daily data consumption by Location.")

# Search Area
col1, col2 = st.columns([1, 3])
with col1:
    player_id_input = st.text_input("Search by Player ID (Tag)", placeholder="Ex: DAL-DDP...")

if player_id_input:
    with st.spinner('Loading data...'):
        df = get_data(player_id_input)

    if not df.empty:
        # Convert Bytes to Megabytes (MB) for readability
        df['total_mb'] = df['total_bytes'] / (1024 * 1024)
        df['total_mb'] = df['total_mb'].round(2)

        # Display global metrics
        st.metric(label="Total Data Consumed (Period)", value=f"{df['total_mb'].sum():.2f} MB")

        # Create chart with Plotly
        fig = px.line(
            df, 
            x='date_log', 
            y='total_mb', 
            color='location_name',
            markers=True,
            title=f"Daily consumption of bsp.exe for tag: {player_id_input}",
            labels={'total_mb': 'Consumption (MB)', 'date_log': 'Date', 'location_name': 'Location'}
        )
        
        # Improve chart layout
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # Display raw data
        with st.expander("View raw data"):
            st.dataframe(df[['date_log', 'location_name', 'player_id', 'total_mb']])
            
    else:
        st.warning("No data found for this Player ID, or 'bsp.exe' application usage not found for this agent.")
else:
    st.info("Please enter a Player ID to start the search.")
