from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


ALIASES = {
    "Data": "DATA",
    "data": "DATA",
    "Empresa": "EMPRESA",
    "Fazenda": "FAZENDA",
    "Município": "MUNICIPIO",
    "Municipio": "MUNICIPIO",
    "AREA_PORDUT": "AREA_PRODU",
    "AREA_PRODUT": "AREA_PRODU",
    "AREA_PRODUTIVA": "AREA_PRODU",
    "PRECIP": "PRECIP_CHIRPS_MM",
    "PRECIP_MM": "PRECIP_CHIRPS_MM",
    "TEMP_MEDIA": "TEMP_MEDIA_C",
    "UMID_MEDIA": "UMID_MEDIA_PCT",
}

NUMERIC_CANDIDATES = [
    "AREA_PRODU",
    "AREA_T",
    "PRECIP_CHIRPS_MM",
    "TEMP_MEDIA_C",
    "TEMP_MIN_C",
    "TEMP_MAX_C",
    "AMPLITUDE_TERMICA_C",
    "UMID_MEDIA_PCT",
    "UMID_MIN_PCT",
    "DIAS_SEM_CHUVA",
    "INDICE_RISCO_INCENDIO",
    "DEFICIT_HIDRICO_MM",
    "INDICE_SECA",
    "RISCO_ESTRESSE_HIDRICO",
    "NOITES_FRIAS_Eucalipto_<15C",
    "NOITES_FRIAS_Pinus_<5C",
    "ONDAS_CALOR_Eucalipto_>35C",
]


def normalize_analysis_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza colunas, datas e números para uso na aba de análise."""
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    out = out.rename(columns={k: v for k, v in ALIASES.items() if k in out.columns})

    if "DATA" in out.columns:
        out["DATA"] = pd.to_datetime(out["DATA"], errors="coerce")
        out = out.dropna(subset=["DATA"]).copy()

    for col in NUMERIC_CANDIDATES:
        if col in out.columns:
            out[col] = coerce_numeric_br(out[col])

    return out


def coerce_numeric_br(series: pd.Series) -> pd.Series:
    """Converte texto numérico BR/EN para float de forma robusta."""
    x = series.astype(str).str.strip()
    x = x.replace({"None": "", "nan": "", "NaN": "", "N/A": "", "-": "", "": np.nan})
    x = x.str.replace(r"[^0-9,\.\-]+", "", regex=True)

    has_dot = x.str.contains(r"\.", na=False)
    has_comma = x.str.contains(r",", na=False)
    both = has_dot & has_comma

    x.loc[both] = x.loc[both].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    only_comma = has_comma & ~has_dot
    x.loc[only_comma] = x.loc[only_comma].str.replace(",", ".", regex=False)

    return pd.to_numeric(x, errors="coerce")


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce")
    mask = v.notna() & w.notna() & (w > 0)
    if mask.sum() == 0:
        return float("nan")
    return float((v[mask] * w[mask]).sum() / w[mask].sum())


def resumo_por_fazenda(df: pd.DataFrame) -> pd.DataFrame:
    """Replica a lógica-base do app de referência para resumo por fazenda."""
    if df is None or df.empty or "FAZENDA" not in df.columns:
        return pd.DataFrame()

    df2 = df.copy()
    for col in NUMERIC_CANDIDATES:
        if col in df2.columns:
            df2[col] = pd.to_numeric(df2[col], errors="coerce")

    agg_dict: Dict[str, str] = {}
    if "AREA_PRODU" in df2.columns:
        agg_dict["AREA_PRODU"] = "first"
    if "AREA_T" in df2.columns:
        agg_dict["AREA_T"] = "first"
    if "PRECIP_CHIRPS_MM" in df2.columns:
        agg_dict["PRECIP_CHIRPS_MM"] = "sum"
    if "TEMP_MEDIA_C" in df2.columns:
        agg_dict["TEMP_MEDIA_C"] = "mean"
    if "TEMP_MIN_C" in df2.columns:
        agg_dict["TEMP_MIN_C"] = "min"
    if "TEMP_MAX_C" in df2.columns:
        agg_dict["TEMP_MAX_C"] = "max"
    if "AMPLITUDE_TERMICA_C" in df2.columns:
        agg_dict["AMPLITUDE_TERMICA_C"] = "mean"
    if "UMID_MIN_PCT" in df2.columns:
        agg_dict["UMID_MIN_PCT"] = "mean"
    if "DIAS_SEM_CHUVA" in df2.columns:
        agg_dict["DIAS_SEM_CHUVA"] = "max"
    if "DEFICIT_HIDRICO_MM" in df2.columns:
        agg_dict["DEFICIT_HIDRICO_MM"] = "sum"
    if "INDICE_SECA" in df2.columns:
        agg_dict["INDICE_SECA"] = "sum"
    if "RISCO_ESTRESSE_HIDRICO" in df2.columns:
        agg_dict["RISCO_ESTRESSE_HIDRICO"] = "mean"
    if "NOITES_FRIAS_Eucalipto_<15C" in df2.columns:
        agg_dict["NOITES_FRIAS_Eucalipto_<15C"] = "sum"
    if "NOITES_FRIAS_Pinus_<5C" in df2.columns:
        agg_dict["NOITES_FRIAS_Pinus_<5C"] = "sum"
    if "ONDAS_CALOR_Eucalipto_>35C" in df2.columns:
        agg_dict["ONDAS_CALOR_Eucalipto_>35C"] = "sum"
    if "UMID_MEDIA_PCT" in df2.columns:
        agg_dict["UMID_MEDIA_PCT"] = "mean"
    if "INDICE_RISCO_INCENDIO" in df2.columns:
        agg_dict["INDICE_RISCO_INCENDIO"] = "max"

    if not agg_dict:
        return pd.DataFrame()

    res = df2.groupby("FAZENDA", dropna=False).agg(agg_dict).round(2)

    rename_map = {
        "PRECIP_CHIRPS_MM": "Soma Precipitação (mm)",
        "TEMP_MEDIA_C": "Média Temp (°C)",
        "TEMP_MIN_C": "Menor Temp Min (°C)",
        "TEMP_MAX_C": "Maior Temp Max (°C)",
        "AMPLITUDE_TERMICA_C": "Média Amplitude Térmica (°C)",
        "UMID_MIN_PCT": "Média Umidade Min (%)",
        "DIAS_SEM_CHUVA": "Máximo Dias Sem Chuva",
        "DEFICIT_HIDRICO_MM": "Soma Déficit Hídrico (mm)",
        "INDICE_SECA": "Soma Índice Seca",
        "RISCO_ESTRESSE_HIDRICO": "Média Risco Estresse Hídrico",
        "NOITES_FRIAS_Eucalipto_<15C": "Soma Noites Frias Eucalipto (<15C)",
        "NOITES_FRIAS_Pinus_<5C": "Soma Noites Frias Pinus (<5C)",
        "ONDAS_CALOR_Eucalipto_>35C": "Soma Ondas de Calor (>35C)",
        "UMID_MEDIA_PCT": "Média Umidade (%)",
        "INDICE_RISCO_INCENDIO": "Máximo Risco Incêndio",
    }
    res = res.rename(columns=rename_map)

    preferred = [
        "AREA_PRODU",
        "AREA_T",
        "Soma Precipitação (mm)",
        "Média Temp (°C)",
        "Menor Temp Min (°C)",
        "Maior Temp Max (°C)",
        "Média Amplitude Térmica (°C)",
        "Média Umidade Min (%)",
        "Máximo Dias Sem Chuva",
        "Soma Déficit Hídrico (mm)",
        "Soma Índice Seca",
        "Média Risco Estresse Hídrico",
        "Soma Noites Frias Eucalipto (<15C)",
        "Soma Noites Frias Pinus (<5C)",
        "Soma Ondas de Calor (>35C)",
        "Média Umidade (%)",
        "Máximo Risco Incêndio",
    ]
    cols_final = [c for c in preferred if c in res.columns] + [c for c in res.columns if c not in preferred]
    return res[cols_final]


def metricas_agregadas_caso_b(df: pd.DataFrame) -> Dict[str, object]:
    """Replica o painel e séries do app de referência."""
    out: Dict[str, object] = {
        "precip_wp": np.nan,
        "temp_mean": np.nan,
        "umid_mean": np.nan,
        "indice_risco_incendio_max": np.nan,
        "deficit_hidrico_soma": np.nan,
        "indice_seca_soma": np.nan,
        "risco_estresse_hidrico_media": np.nan,
        "noites_frias_eucalipto_soma": np.nan,
        "noites_frias_pinus_soma": np.nan,
        "serie_dias_sem_chuva_wp": pd.DataFrame(),
        "serie_indice_risco_incendio": pd.DataFrame(),
        "serie_risco_estresse_hidrico": pd.DataFrame(),
    }

    if df is None or df.empty:
        return out

    df2 = df.copy()
    if "DATA" in df2.columns:
        df2["DATA"] = pd.to_datetime(df2["DATA"], errors="coerce")

    for col in NUMERIC_CANDIDATES:
        if col in df2.columns:
            df2[col] = pd.to_numeric(df2[col], errors="coerce")

    if "TEMP_MEDIA_C" in df2.columns:
        out["temp_mean"] = float(df2["TEMP_MEDIA_C"].mean(skipna=True))
    if "UMID_MEDIA_PCT" in df2.columns:
        out["umid_mean"] = float(df2["UMID_MEDIA_PCT"].mean(skipna=True))
    if "INDICE_RISCO_INCENDIO" in df2.columns:
        out["indice_risco_incendio_max"] = float(df2["INDICE_RISCO_INCENDIO"].max(skipna=True))
    if "DEFICIT_HIDRICO_MM" in df2.columns:
        out["deficit_hidrico_soma"] = float(df2["DEFICIT_HIDRICO_MM"].sum(skipna=True))
    if "INDICE_SECA" in df2.columns:
        out["indice_seca_soma"] = float(df2["INDICE_SECA"].sum(skipna=True))
    if "RISCO_ESTRESSE_HIDRICO" in df2.columns:
        out["risco_estresse_hidrico_media"] = float(df2["RISCO_ESTRESSE_HIDRICO"].mean(skipna=True))
    if "NOITES_FRIAS_Eucalipto_<15C" in df2.columns:
        out["noites_frias_eucalipto_soma"] = float(df2["NOITES_FRIAS_Eucalipto_<15C"].sum(skipna=True))
    if "NOITES_FRIAS_Pinus_<5C" in df2.columns:
        out["noites_frias_pinus_soma"] = float(df2["NOITES_FRIAS_Pinus_<5C"].sum(skipna=True))

    if all(c in df2.columns for c in ["FAZENDA", "AREA_PRODU", "PRECIP_CHIRPS_MM"]):
        areas = df2.groupby("FAZENDA")["AREA_PRODU"].first()
        p_sum = df2.groupby("FAZENDA")["PRECIP_CHIRPS_MM"].sum(min_count=1)
        tmp = pd.concat([areas.rename("A"), p_sum.rename("P")], axis=1).dropna()
        tmp = tmp[tmp["A"] > 0]
        if not tmp.empty:
            out["precip_wp"] = float((tmp["P"] * tmp["A"]).sum() / tmp["A"].sum())

    if all(c in df2.columns for c in ["DATA", "DIAS_SEM_CHUVA", "FAZENDA", "AREA_PRODU"]):
        d3 = df2.dropna(subset=["DATA", "FAZENDA"]).copy()
        area_map = d3.groupby("FAZENDA")["AREA_PRODU"].first()
        d3["PESO_AREA"] = d3["FAZENDA"].map(area_map)
        d3 = d3.dropna(subset=["PESO_AREA"])
        d3 = d3[d3["PESO_AREA"] > 0]
        if not d3.empty:
            s = (
                d3.groupby(d3["DATA"].dt.date)
                .apply(lambda g: weighted_mean(g["DIAS_SEM_CHUVA"], g["PESO_AREA"]), include_groups=False)
                .reset_index(name="DIAS_SEM_CHUVA_MEDIA_PONDERADA")
            )
            s["DATA"] = pd.to_datetime(s["DATA"])
            out["serie_dias_sem_chuva_wp"] = s.sort_values("DATA")

    if all(c in df2.columns for c in ["DATA", "INDICE_RISCO_INCENDIO"]):
        d4 = df2.dropna(subset=["DATA", "INDICE_RISCO_INCENDIO"]).copy()
        d4["DATA"] = pd.to_datetime(d4["DATA"])
        s2 = d4.groupby(d4["DATA"].dt.date)["INDICE_RISCO_INCENDIO"].mean().reset_index(name="INDICE_RISCO_INCENDIO_MEDIA")
        s2["DATA"] = pd.to_datetime(s2["DATA"])
        out["serie_indice_risco_incendio"] = s2.sort_values("DATA")

    if all(c in df2.columns for c in ["DATA", "RISCO_ESTRESSE_HIDRICO"]):
        d5 = df2.dropna(subset=["DATA", "RISCO_ESTRESSE_HIDRICO"]).copy()
        d5["DATA"] = pd.to_datetime(d5["DATA"])
        s3 = d5.groupby(d5["DATA"].dt.date)["RISCO_ESTRESSE_HIDRICO"].mean().reset_index(name="RISCO_ESTRESSE_HIDRICO_MEDIA")
        s3["DATA"] = pd.to_datetime(s3["DATA"])
        out["serie_risco_estresse_hidrico"] = s3.sort_values("DATA")

    return out


def build_diagnostic_summary(df: pd.DataFrame, columns: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    total = len(df)
    for col in columns:
        if col in df.columns:
            out[col] = f"{int(df[col].notna().sum())} / {total}"
    return out
