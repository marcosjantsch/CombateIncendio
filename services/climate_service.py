# -*- coding: utf-8 -*-
# services/climate_service.py

from __future__ import annotations

import io
import os
import logging
from datetime import date
from typing import List, Optional

import pandas as pd
import requests
import streamlit as st

from config_urls import get_url_by_year, load_urls
from core.settings import DADOSONLINE_DIR
from services.date_service import parse_date_safe, enrich_date_columns
from services.log_service import (
    log_error,
    log_error_once,
    log_info_once,
    log_success_once,
    log_warning,
    log_warning_once,
)


logger = logging.getLogger(__name__)
LOCAL_DATA_DIR = str(DADOSONLINE_DIR)


def _filter_signature(filtro: dict) -> dict:
    return {
        "tipo_dado": filtro.get("tipo_dado"),
        "selected_uf": filtro.get("selected_uf"),
        "selected_empresa": filtro.get("selected_empresa"),
        "selected_fazenda": filtro.get("selected_fazenda"),
        "selected_municipio": filtro.get("selected_municipio"),
        "start_date": str(filtro.get("start_date")),
        "end_date": str(filtro.get("end_date")),
        "filters_version": int(filtro.get("filters_version", 0)),
    }


# =====================================================================
# HELPERS
# =====================================================================
def get_years_in_range(start_date: date, end_date: date) -> List[int]:
    if start_date is None or end_date is None or end_date < start_date:
        return []
    return list(range(start_date.year, end_date.year + 1))


def _get_local_csv_path(year: int) -> Optional[str]:
    local_path = os.path.join(LOCAL_DATA_DIR, f"resumo_{int(year)}.csv")
    return local_path if os.path.isfile(local_path) else None


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    rename_map = {
        "Data": "DATA",
        "data": "DATA",
        "Empresa": "EMPRESA",
        "Fazenda": "FAZENDA",
        "Município": "MUNICIPIO",
        "Municipio": "MUNICIPIO",
        "AREA_PORDUT": "AREA_PRODU",
        "AREA_PRODUT": "AREA_PRODU",
        "AREA_PRODUTIVA": "AREA_PRODU",
    }

    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})

    for c in out.columns:
        if out[c].dtype == "object":
            out[c] = out[c].astype(str).str.strip()

    return out


def _preview_bytes(content: bytes, limit: int = 500) -> str:
    try:
        return content[:limit].decode("utf-8", errors="ignore")
    except Exception:
        return "<não foi possível decodificar prévia>"


def _looks_like_excel(content: bytes, content_type: str) -> bool:
    ct = (content_type or "").lower()

    if "spreadsheetml" in ct or "excel" in ct or "officedocument" in ct:
        return True

    if content[:2] == b"PK":
        return True

    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return True

    return False


def _try_read_excel(content: bytes, year: int) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_excel(io.BytesIO(content))

        if df is None or df.empty:
            return None

        df = _normalize_columns(df)
        logger.info("Ano %s: arquivo lido como Excel com %s linhas.", year, len(df))
        return df

    except Exception as e:
        logger.warning("Ano %s: falha ao ler como Excel: %s", year, e)
        return None


def _try_read_csv(content: bytes, year: int) -> Optional[pd.DataFrame]:
    encodings = ["utf-8", "utf-8-sig", "latin-1", "iso-8859-1", "cp1252"]
    separators = [";", ",", "\t", "|"]

    for enc in encodings:
        try:
            text = content.decode(enc)
        except Exception:
            continue

        for sep in separators:
            try:
                df = pd.read_csv(
                    io.StringIO(text),
                    sep=sep,
                    engine="python",
                    on_bad_lines="skip",
                )

                if df is None or df.empty or len(df.columns) <= 1:
                    continue

                df = _normalize_columns(df)
                logger.info(
                    "Ano %s: arquivo lido como CSV (encoding=%s, separador=%r) com %s linhas.",
                    year,
                    enc,
                    sep,
                    len(df),
                )
                return df

            except Exception:
                continue

    logger.warning("Ano %s: não foi possível interpretar o conteúdo como CSV.", year)
    return None


# =====================================================================
# LEITURA ROBUSTA
# =====================================================================
@st.cache_data(show_spinner=False)
def load_csv_from_url_robust(url: str, year: int) -> Optional[pd.DataFrame]:
    try:
        url = str(url).strip().replace("\\", "/")
        is_local_file = os.path.isfile(url)

        if is_local_file:
            with open(url, "rb") as f:
                content = f.read()

            content_type = "arquivo/local"
        else:
            if "1drv.ms" in url and "download=1" not in url:
                url = url + ("&download=1" if "?" in url else "?download=1")

            response = requests.get(
                url,
                timeout=180,
                allow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                },
            )

            response.raise_for_status()
            content = response.content or b""
            content_type = response.headers.get("Content-Type", "N/A")

        if not content:
            logger.warning("Ano %s: resposta vazia.", year)
            return None

        preview = _preview_bytes(content)
        preview_lower = preview.lower()

        if "<html" in preview_lower or "<!doctype html" in preview_lower:
            logger.warning(
                "Ano %s: a origem retornou HTML em vez de CSV/Excel.", year
            )
            return None

        if _looks_like_excel(content, content_type):
            df_excel = _try_read_excel(content, year)
            if df_excel is not None and not df_excel.empty:
                if "DATA" in df_excel.columns:
                    df_excel["DATA"] = parse_date_safe(df_excel["DATA"])
                return df_excel

        df_csv = _try_read_csv(content, year)
        if df_csv is not None and not df_csv.empty:
            if "DATA" in df_csv.columns:
                df_csv["DATA"] = parse_date_safe(df_csv["DATA"])
            return df_csv

        df_excel_fallback = _try_read_excel(content, year)
        if df_excel_fallback is not None and not df_excel_fallback.empty:
            if "DATA" in df_excel_fallback.columns:
                df_excel_fallback["DATA"] = parse_date_safe(df_excel_fallback["DATA"])
            return df_excel_fallback

        logger.warning(
            "Ano %s: conteúdo recebido, mas não foi possível ler como CSV nem Excel.",
            year,
        )
        return None

    except requests.exceptions.RequestException as e:
        logger.error("Erro HTTP/rede ao buscar arquivo do ano %s: %s", year, e)
        return None

    except Exception as e:
        logger.error("Erro inesperado ao carregar arquivo do ano %s: %s", year, e)
        return None


# =====================================================================
# FILTROS
# =====================================================================
def _apply_date_filters(df_csv: pd.DataFrame, filtro: dict) -> pd.DataFrame:
    if df_csv is None or df_csv.empty:
        return pd.DataFrame()

    if "DATA" not in df_csv.columns:
        st.warning("⚠️ Coluna DATA não encontrada após carregamento.")
        return df_csv

    df_csv = df_csv.copy()
    df_csv["DATA"] = parse_date_safe(df_csv["DATA"])
    df_csv = df_csv.dropna(subset=["DATA"]).copy()

    if df_csv.empty:
        st.warning("⚠️ Todos os registros foram descartados após converter DATA.")
        return df_csv

    df_csv = enrich_date_columns(df_csv, "DATA")

    start_period = pd.Period(filtro["start_date"], freq="M")
    end_period = pd.Period(filtro["end_date"], freq="M")

    df_csv["MES_ANO_PERIODO"] = df_csv["DATA"].dt.to_period("M")
    df_csv = df_csv[
        (df_csv["MES_ANO_PERIODO"] >= start_period)
        & (df_csv["MES_ANO_PERIODO"] <= end_period)
    ].copy()

    df_csv.drop(columns=["MES_ANO_PERIODO"], inplace=True, errors="ignore")

    return df_csv


def _apply_dimension_filters(df_csv: pd.DataFrame, filtro: dict) -> pd.DataFrame:
    if df_csv is None or df_csv.empty:
        return pd.DataFrame()

    tipo = filtro["tipo_dado"]

    if tipo == "Dados por Estado" and filtro["selected_uf"] and "UF" in df_csv.columns:
        df_csv = df_csv[df_csv["UF"].astype(str) == str(filtro["selected_uf"])]

    elif (
        tipo == "Dados por Empresa"
        and filtro["selected_empresa"]
        and "EMPRESA" in df_csv.columns
    ):
        df_csv = df_csv[df_csv["EMPRESA"].astype(str) == str(filtro["selected_empresa"])]

    elif (
        tipo == "Dados Empresa/Fazenda"
        and filtro["selected_empresa"]
        and filtro["selected_fazenda"]
        and all(c in df_csv.columns for c in ["EMPRESA", "FAZENDA"])
    ):
        df_csv = df_csv[
            (df_csv["EMPRESA"].astype(str) == str(filtro["selected_empresa"]))
            & (df_csv["FAZENDA"].astype(str) == str(filtro["selected_fazenda"]))
        ]

    elif (
        tipo == "Dados por Município"
        and filtro["selected_uf"]
        and filtro["selected_municipio"]
        and all(c in df_csv.columns for c in ["UF", "MUNICIPIO"])
    ):
        df_csv = df_csv[
            (df_csv["UF"].astype(str) == str(filtro["selected_uf"]))
            & (df_csv["MUNICIPIO"].astype(str) == str(filtro["selected_municipio"]))
        ]

    return df_csv


# =====================================================================
# API PRINCIPAL
# =====================================================================
def load_climate_data(filtro: dict) -> pd.DataFrame:
    df_csv = pd.DataFrame()
    urls = load_urls()
    years = get_years_in_range(filtro["start_date"], filtro["end_date"])
    log_container = filtro.get("log_container")
    filter_signature = _filter_signature(filtro)

    log_info_once(
        "climate_service",
        "load_request",
        "Solicitacao de dados climaticos iniciada",
        {"years": years, **filter_signature},
        signature={"years": years, **filter_signature},
    )

    if not years:
        log_warning_once(
            "climate_service",
            "invalid_date_range",
            "Intervalo de datas invalido ou vazio para carga climatica",
            filter_signature,
            signature=filter_signature,
        )
        if log_container:
            log_container.warning("Intervalo de datas invalido ou vazio.")
        return df_csv

    frames = []

    for y in years:
        year_signature = {**filter_signature, "year": int(y)}

        try:
            url = get_url_by_year(urls, y)
            local_path = _get_local_csv_path(y)
            source = local_path or url

            if not source:
                log_warning_once(
                    "climate_service",
                    f"year_source_missing_{y}",
                    "Nao ha origem configurada para o ano climatico",
                    {"year": int(y), **filter_signature},
                    signature=year_signature,
                )
                if log_container:
                    log_container.warning(f"Sem origem configurada para o ano {y}")
                st.warning(f"Ano {y}: URL nao encontrada no config_urls.py")
                continue

            df_y = load_csv_from_url_robust(source, y)
            used_local_fallback = False

            if (df_y is None or df_y.empty) and local_path and source != local_path:
                used_local_fallback = True
                logger.warning(
                    "Ano %s: falha na origem remota, tentando arquivo local %s.",
                    y,
                    local_path,
                )
                df_y = load_csv_from_url_robust(local_path, y)

            if df_y is None or df_y.empty:
                log_warning_once(
                    "climate_service",
                    f"year_empty_{y}",
                    "Ano climatico sem dados validos",
                    {"year": int(y), **filter_signature},
                    signature={**year_signature, "status": "empty"},
                )
                if log_container:
                    log_container.warning(f"Ano {y} sem dados validos")
                st.error(f"Ano {y}: arquivo nao pode ser carregado.")
                continue

            frames.append(df_y)
            origem = "arquivo local" if ((source == local_path and local_path) or used_local_fallback) else "URL"

            log_success_once(
                "climate_service",
                f"year_loaded_{y}",
                "Ano climatico carregado com sucesso",
                {
                    "year": int(y),
                    "records": int(len(df_y)),
                    "source": origem,
                    **filter_signature,
                },
                signature={
                    **year_signature,
                    "records": int(len(df_y)),
                    "source": origem,
                },
            )

            if log_container:
                log_container.success(f"{y}: carregado via {origem}")

        except Exception as e:
            logger.error("Erro ao processar ano %s: %s", y, e)
            log_error_once(
                "climate_service",
                f"year_error_{y}",
                "Erro ao processar ano climatico",
                {"year": int(y), "error": str(e), **filter_signature},
                signature={**year_signature, "error": str(e)},
            )
            if log_container:
                log_container.error(f"Erro ao ler CSV do ano {y}: {e}")

    if not frames:
        log_warning_once(
            "climate_service",
            "empty_all_years",
            "Nenhum ano gerou dados climaticos validos",
            {"years": years, **filter_signature},
            signature={"years": years, **filter_signature, "status": "no_frames"},
        )
        return pd.DataFrame()

    df_csv = pd.concat(frames, ignore_index=True)
    df_csv = _normalize_columns(df_csv)

    df_csv = _apply_date_filters(df_csv, filtro)
    if df_csv.empty:
        log_warning_once(
            "climate_service",
            "empty_after_date_filter",
            "Nenhum registro restou apos o filtro de data",
            {"years": years, **filter_signature},
            signature={"years": years, **filter_signature, "status": "empty_after_date"},
        )
        st.error("Nenhum registro restou apos o tratamento de DATA/periodo.")
        return df_csv

    df_csv = _apply_dimension_filters(df_csv, filtro)

    total_records = int(len(df_csv))
    if log_container:
        log_container.info(f"Total final: {total_records} registros")

    if total_records == 0:
        log_warning_once(
            "climate_service",
            "empty_after_dimension_filter",
            "Filtro dimensional nao retornou registros climaticos",
            filter_signature,
            signature={**filter_signature, "status": "empty_after_dimension"},
        )
    else:
        log_success_once(
            "climate_service",
            "final_dataset",
            "Dataset climatico final preparado",
            {"records": total_records, "columns": int(len(df_csv.columns)), **filter_signature},
            signature={
                **filter_signature,
                "records": total_records,
                "columns": int(len(df_csv.columns)),
            },
        )

    return df_csv
