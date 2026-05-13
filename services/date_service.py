# -*- coding: utf-8 -*-
# services/date_service.py

from __future__ import annotations

import pandas as pd


def parse_date_safe(series: pd.Series) -> pd.Series:
    """
    Converte uma série para datetime de forma robusta.
    Aceita datas como:
    - 2025-01-01
    - 2025/01/01
    - 01/01/2025
    - strings com espaços
    """
    if series is None:
        return pd.Series(dtype="datetime64[ns]")

    s = series.copy()

    # garante string apenas onde necessário
    if not pd.api.types.is_datetime64_any_dtype(s):
        s = s.astype(str).str.strip()

        # limpa valores vazios ou inválidos comuns
        s = s.replace(
            {
                "": pd.NA,
                "nan": pd.NA,
                "None": pd.NA,
                "NaT": pd.NA,
            }
        )

    # 1ª tentativa: parsing geral
    dt = pd.to_datetime(s, errors="coerce")

    # 2ª tentativa: formato dia/mês/ano para o que falhou
    mask = dt.isna()
    if mask.any():
        dt2 = pd.to_datetime(s[mask], errors="coerce", dayfirst=True)
        dt.loc[mask] = dt2

    return dt


def enrich_date_columns(df: pd.DataFrame, date_col: str = "DATA") -> pd.DataFrame:
    """
    Enriquece o DataFrame com colunas derivadas da data.
    """
    if df is None or df.empty or date_col not in df.columns:
        return df

    out = df.copy()
    out[date_col] = parse_date_safe(out[date_col])

    if out[date_col].isna().all():
        return out

    out["ANO"] = out[date_col].dt.year
    out["MES"] = out[date_col].dt.month
    out["DIA"] = out[date_col].dt.day
    out["MES_ANO"] = out[date_col].dt.strftime("%m/%Y")

    return out
