import io
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

from core.theme_palette import get_theme_palette
from services.log_service import log_error_once, log_info_once, log_success_once, log_warning_once


ALIASES = {
    "Data": "DATA",
    "data": "DATA",
    "Empresa": "EMPRESA",
    "Fazenda": "FAZENDA",
    "Município": "MUNICIPIO",
    "Municipio": "MUNICIPIO",
    "PRECIP": "PRECIP_CHIRPS_MM",
    "PRECIP_MM": "PRECIP_CHIRPS_MM",
    "TEMP_MEDIA": "TEMP_MEDIA_C",
    "UMID_MEDIA": "UMID_MEDIA_PCT",
    "AREA_PORDUT": "AREA_PRODU",
    "AREA_PRODUT": "AREA_PRODU",
    "AREA_PRODUTIVA": "AREA_PRODU",
}

NUMERIC_COLS = [
    "AREA_PRODU",
    "AREA_T",
    "PRECIP_CHIRPS_MM",
    "TEMP_MEDIA_C",
    "TEMP_MIN_C",
    "TEMP_MAX_C",
    "AMPLITUDE_TERMICA_C",
    "UMID_MEDIA_PCT",
    "UMID_MIN_PCT",
    "UMID_MAX_PCT",
    "DIAS_SEM_CHUVA",
    "DEFICIT_HIDRICO_MM",
    "INDICE_SECA",
    "RISCO_ESTRESSE_HIDRICO",
    "INDICE_RISCO_INCENDIO",
    "NOITES_FRIAS_Eucalipto_<15C",
    "NOITES_FRIAS_Pinus_<5C",
    "ONDAS_CALOR_Eucalipto_>35C",
]


def render_tab_analise(
    df_csv,
    tipo_dado=None,
    selected_uf=None,
    selected_municipio=None,
    selected_empresa=None,
    selected_fazenda=None,
    start_date=None,
    end_date=None,
    filters_version: int = 0,
):
    st.markdown('<div class="section-title">Análise Avançada</div>', unsafe_allow_html=True)

    if not st.session_state.get("aplicar", False):
        log_info_once(
            "tab_analise",
            "waiting_filters",
            "Aba Analise Avancada aguardando aplicacao de filtros",
            {},
            signature={"aplicar": False},
        )
        st.info("Clique em '✅ Aplicar Filtros' na sidebar para ver a análise.")
        return

    if df_csv is None or df_csv.empty:
        log_warning_once(
            "tab_analise",
            "empty_dataset",
            "Aba Analise Avancada sem dados filtrados",
            {},
            signature={"empty": True, "filters_version": int(filters_version or 0)},
        )
        st.error("❌ Sem dados filtrados para análise.")
        return

    df = _prepare_dataframe(df_csv)
    if df.empty:
        log_error_once(
            "tab_analise",
            "empty_after_normalization",
            "Normalizacao da analise avancada nao gerou dados validos",
            {"input_records": int(len(df_csv))},
            signature={
                "input_records": int(len(df_csv)),
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("❌ Não há dados válidos para análise após a normalização.")
        return

    filtro_desc = _descricao_filtro(
        tipo_dado=tipo_dado,
        selected_uf=selected_uf,
        selected_municipio=selected_municipio,
        selected_empresa=selected_empresa,
        selected_fazenda=selected_fazenda,
    )
    periodo_desc = (
        f"{start_date.strftime('%m/%Y')} a {end_date.strftime('%m/%Y')}"
        if start_date is not None and end_date is not None
        else "-"
    )

    log_success_once(
        "tab_analise",
        "analysis_ready",
        "Analise avancada preparada com sucesso",
        {
            "records": int(len(df)),
            "tipo_dado": tipo_dado or "",
            "periodo_inicio": str(start_date) if start_date is not None else "",
            "periodo_fim": str(end_date) if end_date is not None else "",
        },
        signature={
            "records": int(len(df)),
            "tipo_dado": tipo_dado or "",
            "periodo_inicio": str(start_date) if start_date is not None else "",
            "periodo_fim": str(end_date) if end_date is not None else "",
            "filters_version": int(filters_version or 0),
        },
    )
    st.success(f"✅ Analisando {len(df)} registros válidos no período selecionado.")

    resumo_mes = _build_resumo_mensal(df)
    resumo_ano = _build_resumo_anual(resumo_mes)

    _render_resumo_executivo(df, filtro_desc, periodo_desc)
    _render_painel_metricas(resumo_mes, resumo_ano, filtro_desc, periodo_desc)
    _render_tabela_resumo_ano(resumo_ano, filtro_desc, periodo_desc)
    _render_tabela_resumo_mes(resumo_mes, filtro_desc, periodo_desc)
    _render_graficos(resumo_mes, resumo_ano, tipo_dado, filtro_desc, periodo_desc)
def _prepare_dataframe(df_csv: pd.DataFrame) -> pd.DataFrame:
    df = df_csv.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={k: v for k, v in ALIASES.items() if k in df.columns})

    if "DATA" not in df.columns:
        return pd.DataFrame()

    if not pd.api.types.is_datetime64_any_dtype(df["DATA"]):
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    df = df.dropna(subset=["DATA"]).copy()

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = _to_float_br(df[col])

    meses_pt = {
        1: "Jan",
        2: "Fev",
        3: "Mar",
        4: "Abr",
        5: "Mai",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Set",
        10: "Out",
        11: "Nov",
        12: "Dez",
    }

    df["ANO"] = df["DATA"].dt.year
    df["MES_NUM"] = df["DATA"].dt.month
    df["MES"] = df["MES_NUM"].map(meses_pt)
    df["MES_ANO"] = df["DATA"].dt.strftime("%Y-%m")

    return df


def _to_float_br(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.replace({"None": "", "nan": "", "NaN": "", "N/A": "", "-": "", "": np.nan})
    s = s.str.replace(r"[^0-9,\.\-]+", "", regex=True)

    has_dot = s.str.contains(r"\.", na=False)
    has_comma = s.str.contains(r",", na=False)
    both = has_dot & has_comma

    s.loc[both] = s.loc[both].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    s.loc[has_comma & ~has_dot] = s.loc[has_comma & ~has_dot].str.replace(",", ".", regex=False)

    return pd.to_numeric(s, errors="coerce")


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = v.notna() & w.notna() & (w > 0)
    if mask.sum() == 0:
        return float("nan")
    return float((v[mask] * w[mask]).sum() / w[mask].sum())


def _primeiro_valor_por_fazenda(g: pd.DataFrame, col: str) -> pd.Series:
    if col not in g.columns or "FAZENDA" not in g.columns:
        return pd.Series(dtype=float)

    tmp = g[["FAZENDA", col, "DATA"]].copy()
    tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
    tmp = tmp.sort_values(["FAZENDA", "DATA"])
    return tmp.groupby("FAZENDA", dropna=False)[col].first()


def _descricao_filtro(
    tipo_dado=None,
    selected_uf=None,
    selected_municipio=None,
    selected_empresa=None,
    selected_fazenda=None,
) -> str:
    if tipo_dado == "Dados por Estado":
        return f"Estado: {selected_uf}" if selected_uf else "Estado"

    if tipo_dado == "Dados por Empresa":
        return f"Empresa: {selected_empresa}" if selected_empresa else "Empresa"

    if tipo_dado == "Dados Empresa/Fazenda":
        if selected_empresa and selected_fazenda:
            return f"Empresa/Fazenda: {selected_empresa} / {selected_fazenda}"
        if selected_empresa:
            return f"Empresa: {selected_empresa}"
        return "Empresa/Fazenda"

    if tipo_dado == "Dados por Município":
        if selected_uf and selected_municipio:
            return f"Município: {selected_municipio} / {selected_uf}"
        if selected_municipio:
            return f"Município: {selected_municipio}"
        return "Município"

    return "Todos os Dados"


def _build_resumo_mensal(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    rows = []

    for mes_ano, g in df.groupby("MES_ANO", dropna=False, sort=True):
        g = g.sort_values("DATA").copy()

        ano = int(g["ANO"].dropna().iloc[0]) if "ANO" in g.columns and g["ANO"].notna().any() else np.nan
        mes_num = int(g["MES_NUM"].dropna().iloc[0]) if "MES_NUM" in g.columns and g["MES_NUM"].notna().any() else np.nan
        mes = g["MES"].dropna().iloc[0] if "MES" in g.columns and g["MES"].notna().any() else None

        row = {
            "MES_ANO": mes_ano,
            "ANO": ano,
            "MES_NUM": mes_num,
            "MES": mes,
        }

        area_t_faz = _primeiro_valor_por_fazenda(g, "AREA_T")
        area_produ_faz = _primeiro_valor_por_fazenda(g, "AREA_PRODU")

        area_t_valid = pd.to_numeric(area_t_faz, errors="coerce").dropna()
        area_t_valid = area_t_valid[area_t_valid > 0]

        area_produ_valid = pd.to_numeric(area_produ_faz, errors="coerce").dropna()
        area_produ_valid = area_produ_valid[area_produ_valid > 0]

        row["AREA_T"] = float(area_t_valid.sum()) if not area_t_valid.empty else np.nan
        row["AREA_PRODU"] = float(area_produ_valid.sum()) if not area_produ_valid.empty else np.nan

        if "PRECIP_CHIRPS_MM" in g.columns:
            precip = pd.to_numeric(g["PRECIP_CHIRPS_MM"], errors="coerce")

            # Mantido conforme sua estrutura atual da tabela mensal
            row["Precipitação Total (mm)"] = _weighted_mean(g["PRECIP_CHIRPS_MM"], g["AREA_PRODU"])
            row["Precipitação Média Ponderada (mm)"] = _weighted_mean(g["PRECIP_CHIRPS_MM"], g["AREA_T"])

            row["Precipitação Máxima (mm)"] = float(precip.max(skipna=True)) if precip.notna().any() else np.nan
            row["Precipitação Mínima (mm)"] = float(precip.min(skipna=True)) if precip.notna().any() else np.nan

        if "TEMP_MEDIA_C" in g.columns:
            row["Média Temp Ponderada (°C)"] = _weighted_mean(g["TEMP_MEDIA_C"], g["AREA_PRODU"])

        if "TEMP_MIN_C" in g.columns:
            tmin = pd.to_numeric(g["TEMP_MIN_C"], errors="coerce")
            row["Temp Mínima (°C)"] = float(tmin.min(skipna=True)) if tmin.notna().any() else np.nan

        if "TEMP_MAX_C" in g.columns:
            tmax = pd.to_numeric(g["TEMP_MAX_C"], errors="coerce")
            row["Temp Máxima (°C)"] = float(tmax.max(skipna=True)) if tmax.notna().any() else np.nan

        if "AMPLITUDE_TERMICA_C" in g.columns:
            row["Amplitude Térmica Ponderada (°C)"] = _weighted_mean(g["AMPLITUDE_TERMICA_C"], g["AREA_PRODU"])

        if "UMID_MEDIA_PCT" in g.columns:
            row["Umidade Média Ponderada (%)"] = _weighted_mean(g["UMID_MEDIA_PCT"], g["AREA_PRODU"])

        if "DIAS_SEM_CHUVA" in g.columns:
            dias_sem = pd.to_numeric(g["DIAS_SEM_CHUVA"], errors="coerce")
            row["Dias sem Chuva"] = float(dias_sem.max(skipna=True)) if dias_sem.notna().any() else np.nan

        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values(["ANO", "MES_NUM", "MES_ANO"]).copy()

    for col in [
        "AREA_T",
        "AREA_PRODU",
        "Precipitação Total (mm)",
        "Precipitação Média Ponderada (mm)",
        "Precipitação Máxima (mm)",
        "Precipitação Mínima (mm)",
        "Média Temp Ponderada (°C)",
        "Temp Mínima (°C)",
        "Temp Máxima (°C)",
        "Amplitude Térmica Ponderada (°C)",
        "Umidade Média Ponderada (%)",
        "Dias sem Chuva",
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    return out


def _build_resumo_anual(resumo_mes: pd.DataFrame) -> pd.DataFrame:
    if resumo_mes is None or resumo_mes.empty:
        return pd.DataFrame()

    rows = []

    for ano, g in resumo_mes.groupby("ANO", dropna=False, sort=True):
        row = {"ANO": int(ano) if pd.notna(ano) else np.nan}

        if "AREA_T" in g.columns:
            area_t = pd.to_numeric(g["AREA_T"], errors="coerce")
            row["AREA_T"] = float(area_t.mean(skipna=True)) if area_t.notna().any() else np.nan

        if "AREA_PRODU" in g.columns:
            area_prod = pd.to_numeric(g["AREA_PRODU"], errors="coerce")
            row["AREA_PRODU"] = float(area_prod.mean(skipna=True)) if area_prod.notna().any() else np.nan

        # Soma anual da precipitação total vinda da tabela mensal
        if "Precipitação Total (mm)" in g.columns:
            precip_total_mes = pd.to_numeric(g["Precipitação Total (mm)"], errors="coerce")
            row["Precipitação Total (mm)"] = (
                float(precip_total_mes.sum(skipna=True))
                if precip_total_mes.notna().any()
                else np.nan
            )

        if "Precipitação Média Ponderada (mm)" in g.columns:
            precip_media = pd.to_numeric(g["Precipitação Média Ponderada (mm)"], errors="coerce")
            row["Precipitação Média Ponderada (mm)"] = (
                float(precip_media.mean(skipna=True))
                if precip_media.notna().any()
                else np.nan
            )

        if "Precipitação Máxima (mm)" in g.columns:
            pmax = pd.to_numeric(g["Precipitação Máxima (mm)"], errors="coerce")
            row["Precipitação Máxima (mm)"] = float(pmax.max(skipna=True)) if pmax.notna().any() else np.nan

        if "Precipitação Mínima (mm)" in g.columns:
            pmin = pd.to_numeric(g["Precipitação Mínima (mm)"], errors="coerce")
            row["Precipitação Mínima (mm)"] = float(pmin.min(skipna=True)) if pmin.notna().any() else np.nan

        if all(c in g.columns for c in ["Média Temp Ponderada (°C)", "AREA_PRODU"]):
            row["Média Temp Ponderada (°C)"] = _weighted_mean(
                g["Média Temp Ponderada (°C)"],
                g["AREA_PRODU"],
            )

        if "Temp Mínima (°C)" in g.columns:
            tmin = pd.to_numeric(g["Temp Mínima (°C)"], errors="coerce")
            row["Temp Mínima (°C)"] = float(tmin.min(skipna=True)) if tmin.notna().any() else np.nan

        if "Temp Máxima (°C)" in g.columns:
            tmax = pd.to_numeric(g["Temp Máxima (°C)"], errors="coerce")
            row["Temp Máxima (°C)"] = float(tmax.max(skipna=True)) if tmax.notna().any() else np.nan

        if all(c in g.columns for c in ["Amplitude Térmica Ponderada (°C)", "AREA_PRODU"]):
            row["Amplitude Térmica Ponderada (°C)"] = _weighted_mean(
                g["Amplitude Térmica Ponderada (°C)"],
                g["AREA_PRODU"],
            )

        if all(c in g.columns for c in ["Umidade Média Ponderada (%)", "AREA_PRODU"]):
            row["Umidade Média Ponderada (%)"] = _weighted_mean(
                g["Umidade Média Ponderada (%)"],
                g["AREA_PRODU"],
            )

        if "Dias sem Chuva" in g.columns:
            dias_sem = pd.to_numeric(g["Dias sem Chuva"], errors="coerce")
            row["Dias sem Chuva"] = float(dias_sem.max(skipna=True)) if dias_sem.notna().any() else np.nan

        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    out = out.sort_values("ANO").copy()
    for col in out.columns:
        if col != "ANO":
            out[col] = pd.to_numeric(out[col], errors="coerce").round(2)

    return out


def _render_resumo_executivo(df: pd.DataFrame, filtro_desc: str, periodo_desc: str) -> None:
    st.markdown("---")
    st.markdown('<div class="section-title">Resumo Executivo</div>', unsafe_allow_html=True)
    st.caption(f"Filtro: {filtro_desc} | Período: {periodo_desc}")

    area_total_analisada = np.nan
    area_produtiva_total = np.nan
    num_fazendas = 0
    num_empresas = 0
    num_registros = len(df)

    try:
        primeiro_mes = df["MES_ANO"].dropna().sort_values().iloc[0]
        df_primeiro_mes = df[df["MES_ANO"] == primeiro_mes].copy()

        if "AREA_T" in df_primeiro_mes.columns and "FAZENDA" in df_primeiro_mes.columns:
            area_t_faz = _primeiro_valor_por_fazenda(df_primeiro_mes, "AREA_T")
            area_total_analisada = float(pd.to_numeric(area_t_faz, errors="coerce").sum(skipna=True))

        if "AREA_PRODU" in df_primeiro_mes.columns and "FAZENDA" in df_primeiro_mes.columns:
            area_prod_faz = _primeiro_valor_por_fazenda(df_primeiro_mes, "AREA_PRODU")
            area_produtiva_total = float(pd.to_numeric(area_prod_faz, errors="coerce").sum(skipna=True))

        if "FAZENDA" in df.columns:
            num_fazendas = int(df["FAZENDA"].dropna().nunique())
        if "EMPRESA" in df.columns:
            num_empresas = int(df["EMPRESA"].dropna().nunique())
    except Exception:
        pass

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Área analisada (ha)", f"{area_total_analisada:.1f}" if pd.notna(area_total_analisada) else "N/A")
    c2.metric("Área produtiva analisada (ha)", f"{area_produtiva_total:.1f}" if pd.notna(area_produtiva_total) else "N/A")
    c3.metric("Fazendas", str(num_fazendas))
    c4.metric("Empresas", str(num_empresas))
    c5.metric("Registros", f"{num_registros:,}".replace(",", "."))


def _render_painel_metricas(resumo_mes: pd.DataFrame, resumo_ano: pd.DataFrame, filtro_desc: str, periodo_desc: str) -> None:
    st.markdown("---")
    st.markdown('<div class="section-title">Painel de Métricas</div>', unsafe_allow_html=True)
    st.caption(f"Filtro: {filtro_desc} | Período: {periodo_desc}")

    precip_total_ponderada = np.nan
    precip_media_anual = np.nan
    precip_media_mensal = np.nan
    precip_maxima = np.nan

    # Soma de todos os valores da coluna "Precipitação Total (mm)" da tabela mensal
    if not resumo_mes.empty and "Precipitação Total (mm)" in resumo_mes.columns:
        serie_total_mes = pd.to_numeric(resumo_mes["Precipitação Total (mm)"], errors="coerce")
        if serie_total_mes.notna().any():
            precip_total_ponderada = float(serie_total_mes.sum(skipna=True))

    # Precipitação total ponderada dividida pelo número de anos selecionados
    if not resumo_ano.empty and "ANO" in resumo_ano.columns and pd.notna(precip_total_ponderada):
        qtd_anos = pd.to_numeric(resumo_ano["ANO"], errors="coerce").dropna().nunique()
        if qtd_anos > 0:
            precip_media_anual = float(precip_total_ponderada / qtd_anos)

    if not resumo_mes.empty and "Precipitação Média Ponderada (mm)" in resumo_mes.columns:
        serie_media = pd.to_numeric(resumo_mes["Precipitação Média Ponderada (mm)"], errors="coerce")
        if serie_media.notna().any():
            precip_media_mensal = float(serie_media.mean(skipna=True))
            precip_maxima = float(serie_media.max(skipna=True))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Precipitação Total Ponderada (mm)", f"{precip_total_ponderada:.2f}" if pd.notna(precip_total_ponderada) else "N/A")
    m2.metric("Precipitação Média Anual (mm)", f"{precip_media_anual:.2f}" if pd.notna(precip_media_anual) else "N/A")
    m3.metric("Precipitação Média Ponderada (mm)", f"{precip_media_mensal:.2f}" if pd.notna(precip_media_mensal) else "N/A")
    m4.metric("Precipitação Máxima (mm)", f"{precip_maxima:.2f}" if pd.notna(precip_maxima) else "N/A")


def _render_tabela_resumo_ano(resumo_ano: pd.DataFrame, filtro_desc: str, periodo_desc: str) -> None:
    st.markdown("---")
    st.markdown('<div class="section-title">Tabela — Resumo por ANO</div>', unsafe_allow_html=True)
    st.caption(f"Filtro: {filtro_desc} | Período: {periodo_desc}")

    if resumo_ano.empty:
        st.warning("⚠️ Não foi possível gerar o resumo por ano.")
        return

    ordem_ano = [
        "ANO",
        "AREA_T",
        "AREA_PRODU",
        "Precipitação Total (mm)",
        "Precipitação Média Ponderada (mm)",
        "Precipitação Máxima (mm)",
        "Precipitação Mínima (mm)",
        "Média Temp Ponderada (°C)",
        "Temp Mínima (°C)",
        "Temp Máxima (°C)",
        "Amplitude Térmica Ponderada (°C)",
        "Umidade Média Ponderada (%)",
        "Dias sem Chuva",
    ]
    resumo_ano_exibir = resumo_ano[[c for c in ordem_ano if c in resumo_ano.columns]].copy()

    st.dataframe(resumo_ano_exibir, width="stretch", height=260)
    st.download_button(
        label="⬇️ Baixar Resumo por ANO (.xlsx)",
        data=_df_to_excel_bytes(resumo_ano_exibir, "Resumo_Ano"),
        file_name="resumo_ano.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_resumo_ano",
    )


def _render_tabela_resumo_mes(resumo_mes: pd.DataFrame, filtro_desc: str, periodo_desc: str) -> None:
    st.markdown("---")
    st.markdown('<div class="section-title">Tabela — Resumo por Mês</div>', unsafe_allow_html=True)
    st.caption(f"Filtro: {filtro_desc} | Período: {periodo_desc}")

    if "mostrar_tudo_resumo_mes" not in st.session_state:
        st.session_state["mostrar_tudo_resumo_mes"] = False

    if resumo_mes.empty:
        st.warning("⚠️ Não foi possível gerar o resumo por mês.")
        return

    ordem_mes = [
        "MES_ANO",
        "ANO",
        "MES",
        "AREA_T",
        "AREA_PRODU",
        "Precipitação Total (mm)",
        "Precipitação Média Ponderada (mm)",
        "Precipitação Máxima (mm)",
        "Precipitação Mínima (mm)",
        "Média Temp Ponderada (°C)",
        "Temp Mínima (°C)",
        "Temp Máxima (°C)",
        "Amplitude Térmica Ponderada (°C)",
        "Umidade Média Ponderada (%)",
        "Dias sem Chuva",
    ]
    resumo_mes_exibir = resumo_mes[[c for c in ordem_mes if c in resumo_mes.columns]].copy()

    st.download_button(
        label="⬇️ Baixar Resumo por MÊS (.xlsx)",
        data=_df_to_excel_bytes(resumo_mes_exibir, "Resumo_Mes"),
        file_name="resumo_mes.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_resumo_mes",
    )

    st.info("Foram exibidos somente os 5 primeiros itens da tabela mensal.")

    if st.button("Exibir tudo", key="btn_exibir_tudo_resumo_mes"):
        st.session_state["mostrar_tudo_resumo_mes"] = True

    if st.session_state["mostrar_tudo_resumo_mes"]:
        st.dataframe(resumo_mes_exibir, width="stretch", height=420)
        st.caption(f"Total de registros mensais: {len(resumo_mes_exibir)}")
    else:
        st.dataframe(resumo_mes_exibir.head(5), width="stretch", height=220)
        st.caption(f"Mostrando 5 de {len(resumo_mes_exibir)} registros mensais.")


def _render_graficos(
    resumo_mes: pd.DataFrame,
    resumo_ano: pd.DataFrame,
    tipo_dado,
    filtro_desc: str,
    periodo_desc: str,
) -> None:
    st.markdown("---")
    palette = get_theme_palette()
    st.markdown('<div class="section-title">Gráficos</div>', unsafe_allow_html=True)
    st.caption(f"Filtro: {filtro_desc} | Período: {periodo_desc}")

    grafico_mes_base = resumo_mes.copy() if not resumo_mes.empty else pd.DataFrame()
    if not grafico_mes_base.empty:
        grafico_mes_base["X_LABEL"] = grafico_mes_base["MES_ANO"].astype(str)

    grafico_ano_base = resumo_ano.copy() if not resumo_ano.empty else pd.DataFrame()
    if not grafico_ano_base.empty:
        grafico_ano_base["X_LABEL"] = grafico_ano_base["ANO"].astype(str)

    def titulo_grafico(base_titulo: str) -> str:
        return f"{base_titulo} | {tipo_dado} | {filtro_desc} | Período: {periodo_desc}"

    def plot_grafico_ano(base_plot: pd.DataFrame, y_col: str, titulo: str, y_axis_title: str):
        if base_plot.empty or y_col not in base_plot.columns:
            st.info(f"Sem dados para exibir o gráfico {titulo}.")
            return

        base_plot = base_plot.dropna(subset=[y_col]).copy()
        if base_plot.empty:
            st.info(f"Sem dados válidos para exibir o gráfico {titulo}.")
            return

        st.markdown(f"**{titulo}**")
        fig = px.bar(
            base_plot,
            x="X_LABEL",
            y=y_col,
            title=titulo_grafico(titulo),
            color_discrete_sequence=palette["plotly_sequence"],
        )
        _apply_plotly_theme(
            fig,
            palette=palette,
            xaxis_title="Ano",
            yaxis_title=y_axis_title,
        )
        st.plotly_chart(fig, width="stretch")

    def plot_grafico_mes(base_plot: pd.DataFrame, y_col: str, titulo: str, y_axis_title: str):
        if base_plot.empty or y_col not in base_plot.columns:
            st.info(f"Sem dados para exibir o gráfico {titulo}.")
            return

        base_plot = base_plot.dropna(subset=[y_col]).copy()
        if base_plot.empty:
            st.info(f"Sem dados válidos para exibir o gráfico {titulo}.")
            return

        st.markdown(f"**{titulo}**")
        fig = px.bar(
            base_plot,
            x="X_LABEL",
            y=y_col,
            title=titulo_grafico(titulo),
            color_discrete_sequence=palette["plotly_sequence"],
        )
        _apply_plotly_theme(
            fig,
            palette=palette,
            xaxis_title="Mês",
            yaxis_title=y_axis_title,
        )
        st.plotly_chart(fig, width="stretch")

    # Sem checkbox, agora com soma por ano
    plot_grafico_ano(
        grafico_ano_base,
        "Precipitação Total (mm)",
        "Precipitação Total por ano",
        "Precipitação Total (mm)",
    )

    # Agora usa os dados mensais da coluna "Precipitação Total (mm)"
    plot_grafico_mes(
        grafico_mes_base,
        "Precipitação Total (mm)",
        "Precipitação Média Ponderada",
        "Precipitação (mm)",
    )

    plot_grafico_mes(
        grafico_mes_base,
        "Média Temp Ponderada (°C)",
        "Média Temp Ponderada",
        "Média Temp Ponderada (°C)",
    )

    plot_grafico_mes(
        grafico_mes_base,
        "Temp Mínima (°C)",
        "Temp Mínima",
        "Temp Mínima (°C)",
    )

    plot_grafico_mes(
        grafico_mes_base,
        "Temp Máxima (°C)",
        "Temp Máxima",
        "Temp Máxima (°C)",
    )

    plot_grafico_mes(
        grafico_mes_base,
        "Umidade Média Ponderada (%)",
        "Umidade Média Ponderada",
        "Umidade Média Ponderada (%)",
    )


def _apply_plotly_theme(
    fig,
    palette: dict,
    xaxis_title: str,
    yaxis_title: str,
) -> None:
    fig.update_layout(
        template="plotly_dark" if palette["mode"] == "dark" else "plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=palette["chart_surface"],
        font={"color": palette["chart_text"]},
        title_font={"color": palette["chart_text"], "size": 16},
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        bargap=0.20,
        colorway=palette["plotly_sequence"],
        margin={"t": 68, "r": 20, "b": 50, "l": 56},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "bgcolor": palette["chart_legend_bg"],
            "bordercolor": palette["panel_border"],
            "borderwidth": 1,
            "font": {"color": palette["chart_text"]},
        },
    )
    fig.update_xaxes(
        type="category",
        showgrid=False,
        showline=True,
        linecolor=palette["chart_domain"],
        tickfont={"color": palette["chart_text"]},
        title_font={"color": palette["chart_text"]},
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=palette["chart_grid"],
        zeroline=True,
        zerolinecolor=palette["chart_grid"],
        showline=True,
        linecolor=palette["chart_domain"],
        tickfont={"color": palette["chart_text"]},
        title_font={"color": palette["chart_text"]},
    )
    fig.update_traces(
        marker_color=palette["plotly_bar"],
        marker_line_color=palette["plotly_bar_line"],
        marker_line_width=1.1,
        hoverlabel={
            "bgcolor": palette["chart_surface"],
            "font_color": palette["chart_text"],
            "bordercolor": palette["panel_border"],
        },
    )


def _df_to_excel_bytes(dataframe: pd.DataFrame, sheet_name: str) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

