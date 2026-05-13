# tabs/tab_shape.py
import pandas as pd
import streamlit as st
from services.export_service import df_to_excel_bytes
from services.log_service import log_info_once, log_success_once, log_warning_once

def render_tab_shape(gdf_filtered, filters_version: int = 0):
    st.markdown('<div class="section-title">Dados Shape</div>', unsafe_allow_html=True)

    if not st.session_state.get("aplicar", False):
        log_info_once(
            "tab_shape",
            "waiting_filters",
            "Aba Dados Shape aguardando aplicacao de filtros",
            {},
            signature={"aplicar": False},
        )
        st.info("Clique em 'Aplicar Filtros' na sidebar para ver os dados do shapefile.")
        return

    if gdf_filtered is None or gdf_filtered.empty:
        log_warning_once(
            "tab_shape",
            "empty_filtered_shape",
            "Aba Dados Shape sem registros filtrados",
            {},
            signature={"empty": True, "filters_version": int(filters_version or 0)},
        )
        st.info("Nenhum dado filtrado para exibir.")
        return

    df_shape = gdf_filtered.copy()
    df_shape = df_shape.drop(columns=["geometry"], errors="ignore")
    df_shape.columns = [str(c).strip() for c in df_shape.columns]

    aliases = {
        "AREA_PORDUT": "AREA_PRODU",
        "AREA_PRODUT": "AREA_PRODU",
        "AREA_PRODUTIVA": "AREA_PRODU",
    }
    df_shape = df_shape.rename(columns={k: v for k, v in aliases.items() if k in df_shape.columns})
    df_shape = df_shape.drop(columns=["LOCAL_PROJ"], errors="ignore")

    for col_area in ["AREA_T", "AREA_PRODU"]:
        if col_area in df_shape.columns:
            df_shape[col_area] = pd.to_numeric(df_shape[col_area], errors="coerce").round(1)

    ordem_prioritaria = [
        "UF", "EMPRESA", "FAZENDA", "MUNICIPIO",
        "AREA_T", "AREA_PRODU", "CENTROIDE_", "CENTROID_1"
    ]
    colunas_existentes = [c for c in ordem_prioritaria if c in df_shape.columns]
    outras_colunas = [c for c in df_shape.columns if c not in colunas_existentes]
    df_shape = df_shape[colunas_existentes + outras_colunas]

    log_success_once(
        "tab_shape",
        "shape_ready",
        "Tabela de shape preparada para exibicao",
        {
            "records": int(len(df_shape)),
            "columns": int(len(df_shape.columns)),
            "filters_version": int(filters_version or 0),
        },
        signature={
            "records": int(len(df_shape)),
            "columns": int(len(df_shape.columns)),
            "filters_version": int(filters_version or 0),
        },
    )

    excel_bytes = df_to_excel_bytes(df_shape, sheet_name="Dados_Shape")

    st.download_button(
        label="⬇️ Exportar para Excel (.xlsx)",
        data=excel_bytes,
        file_name="dados_shape.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.info("Foram exibidas somente as 5 primeiras linhas da tabela.")

    if st.button("Exibir tudo", key="btn_exibir_tudo_shape"):
        st.session_state["mostrar_tudo_shape"] = True

    if st.session_state["mostrar_tudo_shape"]:
        st.dataframe(df_shape, width="stretch", height=520)
        st.caption(f"Total de registros: {len(df_shape)}")
    else:
        st.dataframe(df_shape.head(5), width="stretch", height=220)
        st.caption(f"Mostrando 5 de {len(df_shape)} registros.")
