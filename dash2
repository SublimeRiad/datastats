import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- 1. Page Config & CSS for Dense Dark Layout ---
st.set_page_config(page_title="BSP Monitoring", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS pour forcer le look sombre et dense
st.markdown("""
    <style>
        /* Réduction des marges */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        /* Style des métriques pour le mode sombre */
        div[data-testid="metric-container"] {
            background-color: #262730;
            border: 1px solid #464b5c;
            padding: 10px;
            border-radius: 8px;
            color: white;
        }
        /* Titre plus compact */
        h1 { font-size: 1.8rem !important; margin-bottom: 0 !important; }
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

# --- 3. Data Functions (Cached) ---

@st.cache_data(ttl=300)
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

st.title("📊 BSP.exe Network Monitoring")

df_timeline, df_ranking = get_global_data()

if not df_timeline.empty and not df_ranking.empty:
    df_timeline['total_mb'] = (df_timeline['total_bytes'] / (1024 * 1024)).round(2)
    df_ranking['total_mb'] = (df_ranking['total_bytes'] / (1024 * 1024)).round(2)
    
    total_consumed = df_ranking['total_mb'].sum()
    top_location = df_ranking.iloc[0]['location_name']
    top_val = df_ranking.iloc[0]['total_mb']

    # --- KPI Metrics ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Data (Period)", f"{total_consumed:,.0f} MB")
    kpi2.metric("Top Location", f"{top_location}", f"{top_val:.0f} MB")
    kpi3.metric("Active Locations", f"{df_ranking['location_name'].nunique()}")
    kpi4.metric("Last Log Date", str(df_timeline['date_log'].max()))

    st.markdown("---") # Separator line

    # --- Main Charts ---
    col_left, col_right = st.columns([2, 1])

    # 1. Timeline Chart (Dark Mode optimized)
    with col_left:
        st.subheader("📈 Traffic Over Time")
        fig_time = px.line(
            df_timeline, 
            x='date_log', 
            y='total_mb', 
            color='location_name',
            labels={'total_mb': 'MB', 'date_log': 'Date'},
            height=350,
            template="plotly_dark", # Theme sombre Plotly
            color_discrete_sequence=px.colors.qualitative.Bold # Couleurs vives
        )
        # Force transparent background
        fig_time.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", y=1.1, x=0)
        )
        st.plotly_chart(fig_time, use_container_width=True)

    # 2. Ranking Chart (Dark Mode optimized)
    with col_right:
        st.subheader("🏆 Top Consumers")
        fig_rank = px.bar(
            df_ranking.head(15), 
            x='total_mb', 
            y='location_name', 
            orientation='h',
            color='total_mb', 
            color_continuous_scale='Viridis', # Dégradé néon
            labels={'total_mb': 'MB', 'location_name': ''},
            height=350,
            template="plotly_dark"
        )
        # Force transparent background & reverse y-axis for top 1 at top
        fig_rank.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_rank, use_container_width=True)

else:
    st.warning("No data available. Check database connection.")

# --- 5. Sidebar Search ---
with st.sidebar:
    st.header("🔎 Deep Dive")
    player_input = st.text_input("Search Player Tag", "")
    
    if player_input:
        df_p = get_player_data(player_input)
        if not df_p.empty:
            df_p['total_mb'] = (df_p['total_bytes'] / (1024 * 1024)).round(2)
            st.success(f"Tag: {player_input}")
            st.metric("Total", f"{df_p['total_mb'].sum():.2f} MB")
            
            fig_p = px.area(
                df_p, x='date_log', y='total_mb', 
                template="plotly_dark",
                title="Player Usage"
            )
            fig_p.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0,r=0,t=30,b=0), 
                height=250
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.error("Tag not found.")
