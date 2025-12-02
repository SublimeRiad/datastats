import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Chargement des variables d'environnement (fichier .env)
load_dotenv()

# --- 1. Configuration de la Page & CSS ---
st.set_page_config(page_title="BSP Monitoring", layout="wide", initial_sidebar_state="collapsed")

# CSS personnalisé pour forcer le mode sombre et l'affichage compact
st.markdown("""
    <style>
        /* Force le fond sombre global */
        .stApp {
            background-color: #0E1117;
        }
        
        /* Réduction des marges pour un affichage dense */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* CORRECTION FORCEE DES METRIQUES (KPIs) */
        [data-testid="metric-container"] {
            background-color: #262730 !important;
            border: 1px solid #464b5c !important;
            color: white !important;
            border-radius: 8px;
            padding: 10px 15px;
        }

        /* Couleur des labels des KPIs */
        [data-testid="metric-container"] label, [data-testid="metric-container"] div[data-testid="stMetricLabel"] p {
            color: #a3a8b8 !important;
            font-size: 0.9rem !important;
        }

        /* Couleur des valeurs des KPIs */
        [data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-size: 1.6rem !important;
        }

        /* Style du titre principal */
        h1 { 
            color: white !important;
            font-size: 1.5rem !important; 
            margin-bottom: 0 !important; 
        }
        
        /* Style des sous-titres de graphiques */
        .chart-title {
            font-size: 1rem;
            font-weight: bold;
            color: #FAFAFA;
            margin-bottom: 5px;
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. Connexion Base de Données ---
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
        st.error(f"Erreur de connexion DB : {e}")
        return None

# --- 3. Récupération des Données (Mise en cache) ---

@st.cache_data(ttl=300) # Mise à jour toutes les 5 minutes
def get_global_data():
    conn = init_connection()
    if conn is None: return pd.DataFrame(), pd.DataFrame()
    
    # Requête 1 : Timeline groupée par Date ET Location
    query_timeline = """
    SELECT 
        ns.date_log, 
        l.name as location_name, 
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM glpi_network_stats ns
    JOIN glpi_computers c ON ns.computers_id = c.id
    JOIN glpi_locations l ON c.locations_id = l.id
    WHERE ns.app_name LIKE '%bsp.exe%'
    GROUP BY ns.date_log, l.name
    ORDER BY ns.date_log ASC;
    """
    
    # Requête 2 : Classement global par Location
    query_ranking = """
    SELECT 
        l.name as location_name, 
        SUM(ns.total_sent + ns.total_received) as total_bytes
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
    except Exception as e:
        st.error(f"Erreur SQL Global: {e}")
        if conn.is_connected(): conn.close()
        return pd.DataFrame(), pd.DataFrame()

def get_player_data(player_tag):
    conn = init_connection()
    if conn is None: return pd.DataFrame()
    
    query = """
    SELECT 
        ns.date_log, 
        l.name as location_name, 
        a.tag as player_id,
        SUM(ns.total_sent + ns.total_received) as total_bytes
    FROM glpi_network_stats ns
    JOIN glpi_computers c ON ns.computers_id = c.id
    JOIN glpi_locations l ON c.locations_id = l.id
    JOIN glpi_agents a ON a.items_id = c.id AND a.itemtype = 'Computer'
    WHERE ns.app_name LIKE '%bsp.exe%' 
    AND a.tag LIKE %s
    GROUP BY ns.date_log, l.name, a.tag 
    ORDER BY ns.date_log ASC;
    """
    try:
        df = pd.read_sql(query, conn, params=(f"%{player_tag}%",))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erreur SQL Player: {e}")
        if conn.is_connected(): conn.close()
        return pd.DataFrame()

# --- 4. Affichage Principal ---

st.title("📊 BSP.exe Network Monitoring")

# Chargement des données
df_timeline, df_ranking = get_global_data()

if not df_timeline.empty and not df_ranking.empty:
    # Conversion Bytes -> MB
    df_timeline['total_mb'] = (df_timeline['total_bytes'] / (1024 * 1024)).round(2)
    df_ranking['total_mb'] = (df_ranking['total_bytes'] / (1024 * 1024)).round(2)
    
    # Calcul des KPIs
    total_consumed = df_ranking['total_mb'].sum()
    top_loc_name = df_ranking.iloc[0]['location_name']
    top_loc_val = df_ranking.iloc[0]['total_mb']
    nb_locations = df_ranking['location_name'].nunique()
    last_date = df_timeline['date_log'].max()

    # --- LIGNE 1 : KPIs ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Data (Global)", f"{total_consumed:,.0f} MB")
    k2.metric("Top Location", f"{top_loc_name}", f"{top_loc_val:.0f} MB")
    k3.metric("Active Locations", f"{nb_locations}")
    k4.metric("Last Update", str(last_date))

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # --- LIGNE 2 : Graphiques ---
    col_left, col_right = st.columns([2, 1])

    # Graphique Gauche : Timeline par Location
    with col_left:
        st.markdown('<p class="chart-title">📈 Daily Consumption by Location</p>', unsafe_allow_html=True)
        fig_time = px.line(
            df_timeline, 
            x='date_log', 
            y='total_mb', 
            color='location_name', # Une ligne par couleur de location
            labels={'total_mb': 'MB', 'date_log': '', 'location_name': 'Loc'},
            height=380,
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_time.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", y=1.1, x=0),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#444')
        )
        st.plotly_chart(fig_time, use_container_width=True)

    # Graphique Droite : Top 10 Classement
    with col_right:
        st.markdown('<p class="chart-title">🏆 Top 10 Locations</p>', unsafe_allow_html=True)
        fig_rank = px.bar(
            df_ranking.head(10), 
            x='total_mb', 
            y='location_name', 
            orientation='h',
            color='total_mb', 
            color_continuous_scale='Viridis',
            labels={'total_mb': 'MB', 'location_name': ''},
            height=380,
            template="plotly_dark"
        )
        fig_rank.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis={'categoryorder':'total ascending'},
            xaxis=dict(showgrid=True, gridcolor='#444'),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig_rank, use_container_width=True)

else:
    st.info("Aucune donnée disponible. Vérifiez que l'application 'bsp.exe' est bien présente dans les logs.")

# --- 5. Sidebar (Menu Latéral) : Recherche ---
with st.sidebar:
    st.header("🔎 Player Inspection")
    st.caption("Rechercher un équipement spécifique par son Tag.")
    
    player_input = st.text_input("Player Tag (ex: DAL-DDP...)", "")
    
    if player_input:
        with st.spinner("..."):
            df_p = get_player_data(player_input)
        
        if not df_p.empty:
            df_p['total_mb'] = (df_p['total_bytes'] / (1024 * 1024)).round(2)
            
            st.success(f"Found: {player_input}")
            st.metric("Total Consumed", f"{df_p['total_mb'].sum():.2f} MB")
            
            # Petit graph dans la sidebar
            fig_p = px.area(
                df_p, x='date_log', y='total_mb',
                title="Usage Trend",
                template="plotly_dark"
            )
            fig_p.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0,r=0,t=30,b=0), 
                height=200,
                showlegend=False
            )
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.warning("Tag introuvable.")
