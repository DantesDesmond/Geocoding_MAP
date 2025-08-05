import streamlit as st
import folium
from streamlit_folium import folium_static
from overpass_utils import obtener_negocios, extraer_coordenadas
from clustering import aplicar_dbscan
from branca.element import Element
from jinja2 import Template
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from folium.plugins import FloatImage, MiniMap

# Configuración de la app
st.set_page_config(page_title="Mapa Comercial RD", layout="wide")
st.markdown("""
    <style>
    body {
        background-color: #f8f9fa;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-image: url('https://www.transparenttextures.com/patterns/white-wall-3.png');
        background-repeat: repeat;
    }

    .stApp {
        background-color: #f8f9fa;
    }

    .metric-label {
        font-weight: bold !important;
        color: #343a40 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📍 Mapa Inteligente de Oportunidades Comerciales, Portafolio")

st.markdown("Visualiza dónde hay mayor o menor concentración de negocios en República Dominicana para enfocar tus esfuerzos de ventas.")

CATEGORIAS_DISPONIBLES = {
    "Restaurantes": "restaurant",
    "Bares": "bar",
    "Hoteles": "hotel",
    "Bancos": "bank",
    "Farmacias": "pharmacy",
    "Clínicas": "clinic",
    "Cajeros automáticos": "atm",
    "Supermercados": "supermarket",
    "Estaciones de servicio": "fuel"
}

ciudades = st.multiselect("📍 Ciudades", [
    "Santo Domingo", "Santiago", "La Romana", "San Pedro", 
    "La Vega", "San Francisco de Macorís", "Puerto Plata"
], default=["Santo Domingo"])
categoria_legible = st.selectbox("🏷️ Tipo de negocio", list(CATEGORIAS_DISPONIBLES.keys()))
categoria = CATEGORIAS_DISPONIBLES[categoria_legible]

if st.button("🔍 Buscar negocios"):
    try:
        elementos_totales = []
        for ciudad in ciudades:
            try:
                resultado = obtener_negocios(categoria, ciudad)

                if isinstance(resultado, dict) and "elements" in resultado:
                    elementos = resultado["elements"]
                elif isinstance(resultado, list):
                    elementos = resultado
                else:
                    elementos = []

                for el in elementos:
                    el["ciudad"] = ciudad
                elementos_totales.extend(elementos)

            except Exception as e:
                st.warning(f"No se pudo obtener datos para {ciudad}: {e}")

        # Filtrar solo elementos que correspondan a ciudades seleccionadas
        elementos_filtrados = [el for el in elementos_totales if el.get("ciudad") in ciudades]

        negocios = extraer_coordenadas(elementos_filtrados)
        st.write(f"🔎 Se encontraron {len(negocios)} negocios tipo '{categoria_legible}' en {', '.join(ciudades)}.")

        if negocios:
            df_cluster = aplicar_dbscan(negocios)

            cluster_counts = df_cluster[df_cluster["cluster"] != -1]["cluster"].value_counts().reset_index()
            cluster_counts.columns = ["cluster", "count"]
            cluster_counts["rank"] = cluster_counts["count"].rank(method="first", ascending=False).astype(int)

            colores_densidad = ["red", "orange", "green", "blue", "purple", "darkgreen", "darkred", "cadetblue", "black"]
            cluster_color_map = {
                row["cluster"]: colores_densidad[(row["rank"] - 1) % len(colores_densidad)]
                for _, row in cluster_counts.iterrows()
            }

            lat_mean = df_cluster["lat"].mean()
            lon_mean = df_cluster["lon"].mean()
            mapa = folium.Map(location=[lat_mean, lon_mean], zoom_start=10)

            minimapa = MiniMap(toggle_display=True)
            mapa.add_child(minimapa)

            for _, fila in df_cluster.iterrows():
                cluster_id = int(fila["cluster"])
                color = cluster_color_map.get(cluster_id, "lightgray") if cluster_id != -1 else "lightgray"

                folium.CircleMarker(
                    location=[fila["lat"], fila["lon"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"{fila['nombre']} (Cluster {cluster_id})"
                ).add_to(mapa)

            contenido_leyenda = "<b>🗺️ Leyenda de Clusters</b><br><br>"
            for _, row in cluster_counts.iterrows():
                cluster_num = row["cluster"]
                cluster_count = row["count"]
                color = cluster_color_map.get(cluster_num, "black")
                contenido_leyenda += f"<span style='color:{color}; font-size:16px;'>●</span> Cluster {cluster_num} – {cluster_count} negocios<br>"

            contenido_leyenda += "<br><span style='color:dimgray; font-size:16px;'>●</span> Punto aislado (sin cluster)<br>"

            html = f"""
            <div style="
                position: absolute;
                bottom: 60px;
                left: 30px;
                width: 250px;
                background-color: white;
                border: 2px solid gray;
                z-index: 9999;
                font-size: 14px;
                padding: 10px;">
                {contenido_leyenda}
            </div>
            """
            leyenda = Element(html)
            mapa.get_root().html.add_child(leyenda)

            # KPIs
            total_negocios = len(df_cluster)
            total_clusters = df_cluster[df_cluster["cluster"] != -1]["cluster"].nunique()
            promedio_x_cluster = int(df_cluster[df_cluster["cluster"] != -1].shape[0] / total_clusters) if total_clusters > 0 else 0

            ciudad_top = df_cluster["ciudad"].value_counts().idxmax() if "ciudad" in df_cluster.columns else "-"
            ciudad_top_total = df_cluster["ciudad"].value_counts().max() if "ciudad" in df_cluster.columns else 0

            st.markdown("## 📊 Resumen de Resultados")
            col1, col2, col3, col4 = st.columns(4)

            col1.metric("🔢 Total negocios", total_negocios)
            col2.metric("🧩 Clusters detectados", total_clusters)
            col3.metric("🏪 Promedio por cluster", promedio_x_cluster)
            col4.metric(f"📍 Más negocios en", f"{ciudad_top} ({ciudad_top_total})")

            folium_static(mapa, width=1800, height=600)

            st.subheader("📄 Detalle de negocios agrupados")
        

            df_cluster["cluster"] = df_cluster["cluster"].astype(str)
            df_cluster["categoria"] = categoria_legible
            df_cluster_detalle = df_cluster[["nombre", "lat", "lon", "cluster", "categoria", "ciudad"]]

            st.dataframe(df_cluster_detalle, use_container_width=True)

            st.subheader("📊 Cantidad de negocios por cluster")
            cluster_bar_data = df_cluster["cluster"].value_counts().sort_index()
            st.bar_chart(cluster_bar_data)

            csv = df_cluster_detalle.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", data=csv, file_name="negocios_agrupados.csv", mime="text/csv")

        else:
            st.warning("No se encontraron resultados.")

    except Exception as e:
        st.error(f"Ocurrió un error: {e}")
