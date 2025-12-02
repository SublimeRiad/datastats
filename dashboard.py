import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px
import os
from dotenv import load_dotenv

# Chargement des variables de sécurité depuis le fichier .env
load_dotenv()

# Configuration de la page
st.set_page_config(page_title="Consommation BSP.exe", layout="wide")

# Fonction de connexion à la base de données
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

# Fonction pour récupérer les données
def get_data(player_id):
    conn = init_connection()
    if conn is None:
        return pd.DataFrame()

    # La requête SQL joint les 4 tables nécessaires
    # On filtre sur bsp.exe et sur le TAG (Player ID)
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
        # Utilisation de pandas pour lire directement en DataFrame
        # Le %s est remplacé par le player_id de manière sécurisée
        df = pd.read_sql(query, conn, params=(f"%{player_id}%",))
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erreur lors de la requête : {e}")
        conn.close()
        return pd.DataFrame()

# --- Interface Utilisateur ---

st.title("📊 Analyse Consommation Données - bsp.exe")
st.markdown("Visualisation de la consommation journalière par Location.")

# Zone de recherche
col1, col2 = st.columns([1, 3])
with col1:
    player_id_input = st.text_input("Rechercher par Player ID (Tag)", placeholder="Ex: DAL-DDP...")

if player_id_input:
    with st.spinner('Chargement des données...'):
        df = get_data(player_id_input)

    if not df.empty:
        # Conversion des Octets en Mégaoctets (MB) pour la lisibilité
        df['total_mb'] = df['total_bytes'] / (1024 * 1024)
        df['total_mb'] = df['total_mb'].round(2)

        # Affichage des métriques globales
        st.metric(label="Total Données Consommées (Période)", value=f"{df['total_mb'].sum():.2f} MB")

        # Création du graphique avec Plotly
        fig = px.line(
            df, 
            x='date_log', 
            y='total_mb', 
            color='location_name',
            markers=True,
            title=f"Consommation journalière de bsp.exe pour le tag: {player_id_input}",
            labels={'total_mb': 'Consommation (MB)', 'date_log': 'Date', 'location_name': 'Localisation'}
        )
        
        # Amélioration du graphique
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # Affichage des données brutes
        with st.expander("Voir les données brutes"):
            st.dataframe(df[['date_log', 'location_name', 'player_id', 'total_mb']])
            
    else:
        st.warning("Aucune donnée trouvée pour ce Player ID ou application bsp.exe introuvable pour cet agent.")
else:
    st.info("Veuillez entrer un Player ID pour commencer la recherche.")
