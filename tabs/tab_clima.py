import pandas as pd
import streamlit as st

from services.export_service import df_to_excel_bytes
from services.date_service import enrich_date_columns
from services.log_service import log_error_once, log_info_once, log_success_once, log_warning_once


def _to_float_br(series: pd.Series) -> pd.Series:
    """
    Converte números em formato brasileiro:
    47,62 -> 47.62
    1.234,56 -> 1234.56
    """
    if series is None:
        return series

    s = series.astype(str).str.strip()

    # remove separador de milhar e troca vírgula decimal por ponto
    s = s.str.replace(".", "", regex=False)
    s = s.str.replace(",", ".", regex=False)

    # limpa textos vazios
    s = s.replace({"": None, "None": None, "nan": None, "NaN": None})

    return pd.to_numeric(s, errors="coerce")


def render_tab_clima(df_csv, filters_version: int = 0):
    st.markdown('<div class="section-title">Dados de Clima</div>', unsafe_allow_html=True)

    if not st.session_state.get("aplicar", False):
        log_info_once(
            "tab_clima",
            "waiting_filters",
            "Aba Dados de Clima aguardando aplicacao de filtros",
            {},
            signature={"aplicar": False},
        )
        st.info("Clique em 'Aplicar Filtros' na sidebar para carregar os dados de clima.")
        return

    if df_csv is None or df_csv.empty:
        log_warning_once(
            "tab_clima",
            "empty_dataset",
            "Aba Dados de Clima sem registros filtrados",
            {},
            signature={"empty": True, "filters_version": int(filters_version or 0)},
        )
        st.warning("Nenhum dado de clima filtrado.")
        return

    dfc = df_csv.copy()
    dfc.columns = [str(c).strip() for c in dfc.columns]

    # Padronização de aliases
    aliases = {
        "Data": "DATA",
        "data": "DATA",
        "AREA_PORDUT": "AREA_PRODU",
        "AREA_PRODUT": "AREA_PRODU",
        "AREA_PRODUTIVA": "AREA_PRODU",
    }
    dfc = dfc.rename(columns={k: v for k, v in aliases.items() if k in dfc.columns})

    if "DATA" not in dfc.columns:
        log_error_once(
            "tab_clima",
            "missing_data_column",
            "Coluna DATA ausente na aba Dados de Clima",
            {"columns": [str(c) for c in dfc.columns]},
            signature={
                "columns": [str(c) for c in dfc.columns],
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("❌ Coluna DATA não encontrada.")
        st.write("Colunas disponíveis:", list(dfc.columns))
        return

    # Enriquece datas
    dfc = enrich_date_columns(dfc, "DATA")

    if dfc.empty:
        log_warning_once(
            "tab_clima",
            "empty_after_data_enrichment",
            "Nenhum registro valido restou apos tratamento de DATA",
            {},
            signature={
                "empty_after_data": True,
                "filters_version": int(filters_version or 0),
            },
        )
        st.warning("Nenhum registro válido após o tratamento da coluna DATA.")
        return

    # Conversão correta de áreas com vírgula decimal
    if "AREA_T" in dfc.columns:
        dfc["AREA_T"] = _to_float_br(dfc["AREA_T"])

    if "AREA_PRODU" in dfc.columns:
        dfc["AREA_PRODU"] = _to_float_br(dfc["AREA_PRODU"])

    # Ordena pela data para garantir que o primeiro valor do mês seja o válido
    dfc = dfc.sort_values("DATA").copy()

    # Para cada empresa/fazenda/mês, mantém o primeiro valor de área do mês
    group_keys = ["EMPRESA", "FAZENDA", "MES_ANO"]
    area_cols = [c for c in ["AREA_T", "AREA_PRODU"] if c in dfc.columns]

    if all(c in dfc.columns for c in group_keys) and area_cols:
        df_area_mes = (
            dfc.groupby(group_keys, as_index=False)[area_cols]
            .first()
        )

        dfc = dfc.drop(columns=area_cols, errors="ignore")

        dfc = dfc.merge(
            df_area_mes,
            on=group_keys,
            how="left"
        )

    # Arredondamento final
    for col in ["AREA_T", "AREA_PRODU"]:
        if col in dfc.columns:
            dfc[col] = pd.to_numeric(dfc[col], errors="coerce").round(2)

    with st.expander("Diagnóstico de áreas", expanded=False):
        st.write("Colunas disponíveis:", list(dfc.columns))
        if "AREA_T" in dfc.columns:
            st.write("AREA_T não nulos:", int(dfc["AREA_T"].notna().sum()))
            st.write("Exemplo AREA_T:", dfc["AREA_T"].dropna().head(10).tolist())
        if "AREA_PRODU" in dfc.columns:
            st.write("AREA_PRODU não nulos:", int(dfc["AREA_PRODU"].notna().sum()))
            st.write("Exemplo AREA_PRODU:", dfc["AREA_PRODU"].dropna().head(10).tolist())

    # Remove a coluna DATA da visualização final
    if "DATA" in dfc.columns:
        dfc = dfc.drop(columns=["DATA"])

    # Organização das colunas finais
    colunas_prioritarias = [
        "EMPRESA",
        "FAZENDA",
        "UF",
        "MUNICIPIO",
        "AREA_T",
        "AREA_PRODU",
        "ANO",
        "MES",
        "MES_NOME",
        "MES_ANO",
    ]
    colunas_prioritarias = [c for c in colunas_prioritarias if c in dfc.columns]
    colunas_restantes = [c for c in dfc.columns if c not in colunas_prioritarias]
    dfc = dfc[colunas_prioritarias + colunas_restantes]

    log_success_once(
        "tab_clima",
        "climate_table_ready",
        "Tabela climatica preparada para exibicao",
        {
            "records": int(len(dfc)),
            "columns": int(len(dfc.columns)),
            "filters_version": int(filters_version or 0),
        },
        signature={
            "records": int(len(dfc)),
            "columns": int(len(dfc.columns)),
            "filters_version": int(filters_version or 0),
        },
    )

    # Exportação sem DATA
    df_export = dfc.copy()
    if "DATA" in df_export.columns:
        df_export = df_export.drop(columns=["DATA"])

    excel_bytes = df_to_excel_bytes(df_export, sheet_name="Dados_Clima")

    st.download_button(
        label="⬇️ Exportar para Excel (.xlsx)",
        data=excel_bytes,
        file_name="dados_clima.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    if st.session_state.get("mostrar_tudo_clima", False):
        st.dataframe(dfc, width="stretch", height=520)
        st.caption(f"Total de registros: {len(dfc)}")
    else:
        st.info("Foram exibidas somente as 5 primeiras linhas da tabela.")
        if st.button("Exibir tudo", key="btn_exibir_tudo_clima"):
            st.session_state["mostrar_tudo_clima"] = True
            st.rerun()

        st.dataframe(dfc.head(5), width="stretch", height=220)
        st.caption(f"Mostrando 5 de {len(dfc)} registros.")
