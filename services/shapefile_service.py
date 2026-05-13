# services/shapefile_service.py
import os
from typing import Optional
import geopandas as gpd
import streamlit as st
from core.settings import SIMPLIFICATION_TOLERANCE

@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def load_shapefile_full(file_path: str) -> Optional[gpd.GeoDataFrame]:
    logger.info("Carregando shapefile: %s", file_path)

    if not os.path.exists(file_path):
        logger.warning("Shapefile não encontrado: %s", file_path)
        return None

    try:
        gdf = gpd.read_file(file_path)

        if gdf.empty:
            return gdf

        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")

        if str(gdf.crs).upper() != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        # guarda a geometria original
        gdf["__geometry_original__"] = gdf.geometry.copy()

        try:
            gdf["geometry"] = gdf.geometry.simplify(
                SIMPLIFICATION_TOLERANCE,
                preserve_topology=True,
            )
        except Exception as e:
            logger.warning("Falha na simplificação do shapefile: %s", e)

        return gdf

    except Exception as e:
        logger.error("Erro ao carregar shapefile: %s", e)
        return None

def filter_gdf(gdf, filtro):
    gdf_filtered = gdf.copy()
    tipo = filtro["tipo_dado"]

    if tipo == "Dados por Estado" and filtro["selected_uf"] and "UF" in gdf_filtered.columns:
        gdf_filtered = gdf_filtered[gdf_filtered["UF"].astype(str) == str(filtro["selected_uf"])]

    elif tipo == "Dados por Empresa" and filtro["selected_empresa"] and "EMPRESA" in gdf_filtered.columns:
        gdf_filtered = gdf_filtered[gdf_filtered["EMPRESA"].astype(str) == str(filtro["selected_empresa"])]

    elif (
        tipo == "Dados Empresa/Fazenda"
        and filtro["selected_empresa"]
        and filtro["selected_fazenda"]
        and all(c in gdf_filtered.columns for c in ["EMPRESA", "FAZENDA"])
    ):
        gdf_filtered = gdf_filtered[
            (gdf_filtered["EMPRESA"].astype(str) == str(filtro["selected_empresa"])) &
            (gdf_filtered["FAZENDA"].astype(str) == str(filtro["selected_fazenda"]))
        ]

    elif (
        tipo == "Dados por Município"
        and filtro["selected_uf"]
        and filtro["selected_municipio"]
        and all(c in gdf_filtered.columns for c in ["UF", "MUNICIPIO"])
    ):
        gdf_filtered = gdf_filtered[
            (gdf_filtered["UF"].astype(str) == str(filtro["selected_uf"])) &
            (gdf_filtered["MUNICIPIO"].astype(str) == str(filtro["selected_municipio"]))
        ]

    return gdf_filtered