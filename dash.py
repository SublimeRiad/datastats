import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Chargement des variables de sécurité
load_dotenv()

# Configuration de la page
st.set_page_config(page_title="Dashboard BSP.exe", layout="wide")

# Fonction de connexion
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
        st.error(f"Erreur de connexion à la base de données : {e}")
        return None

# 1. Fonction pour les données détaillées (Par Player ID)
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
        st.error(f"Erreur requête joueur : {e}")
        conn.close()
        return pd.DataFrame()

# 2. Fonction pour les statistiques globales (Par Location)
def get_global_stats():
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
        st.error(f"Erreur requête globale : {e}")
        conn.close()
        return pd.DataFrame()

# --- Interface Utilisateur ---

st.title("📊 Dashboard Consommation - bsp.exe")

# Zone de Recherche
st.subheader("🔎 Recherche par Player ID")
col1, col2 = st.columns([1, 3])
with col1:
    player_id_input = st.text_input("Entrez un Tag (ex: DAL-DDP...)", "")

# Affichage des résultats de recherche (Si une recherche est faite)
if player_id_input:
    with st.spinner(f'Chargement des données pour {player_id_input}...'):
        df_player = get_player_data(player_id_input)

    if not df_player.empty:
        df_player['total_mb'] = (df_player['total_bytes'] / (1024 * 1024)).round(2)
        
        st.success(f"Données trouvées pour : {player_id_input}")
        
        # Métrique pour le joueur
        st.metric("Total Consommé (Ce tag)", f"{df_player['total_mb'].sum():.2f} MB")
        
        # Graphique Ligne (Temporel)
        fig_player = px.line(
            df_player, 
            x='date_log', 
            y='total_mb', 
            color='location_name',
            markers=True,
            title=f"Évolution journalière pour {player_id_input}",
            labels={'total_mb': 'Consommation (MB)', 'date_log': 'Date'}
        )
        st.plotly_chart(fig_player, use_container_width=True)
    else:
        st.warning("Aucune donnée trouvée pour ce Player ID.")

st.divider() 

# --- Section Globale (Ajoutée) ---
st.subheader("🌍 Vue Globale : Consommation Totale par Location")
st.markdown("Ce graphique montre le volume total de données consommées par **tous** les players 'bsp.exe', groupés par lieu.")

with st.spinner('Chargement des statistiques globales...'):
    df_global = get_global_stats()

if not df_global.empty:
    # Conversion en MB (ou GB si c'est très grand, ici on garde MB pour cohérence)
    df_global['total_mb'] = (df_global['total_bytes'] / (1024 * 1024)).round(2)

    # Graphique à Barres (Comparaison des lieux)
    fig_global = px.bar(
        df_global, 
        x='location_name', 
        y='total_mb',
        color='total_mb',
        title="Classement des Locations par Consommation de Données",
        labels={'total_mb': 'Total Consommé (MB)', 'location_name': 'Lieu'},
        color_continuous_scale='Viridis'
    )
    fig_global.update_layout(xaxis_tickangle=-45) # Incliner les labels si les noms sont longs
    st.plotly_chart(fig_global, use_container_width=True)
    
    # Optionnel : Afficher le tableau de données brut dans un "expander"
    with st.expander("Voir le tableau des données par location"):
        st.dataframe(df_global[['location_name', 'total_mb']])
else:
    st.info("Pas de données globales disponibles pour le moment.")
