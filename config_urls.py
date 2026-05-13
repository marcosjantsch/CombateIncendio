# -*- coding: utf-8 -*-
"""
config_urls.py — mapeia ANO -> URL do CSV.

Edite este arquivo e substitua as URLs de exemplo pelas URLs reais.
"""
import logging

logger = logging.getLogger(__name__)

CSV_URLS = {
    # Exemplos (troque por URLs reais):
    2010: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2010.csv",
    2011: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2011.csv",
    2012: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2012.csv",
    2013: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2013.csv",
    2014: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2014.csv",
    2015: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2015.csv",
    2016: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2016.csv",
    2017: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2017.csv",
    2018: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2018.csv",
    2019: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2019.csv",
    2020: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2020.csv",
    2021: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2021.csv",
    2022: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2022.csv",
    2023: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2023.csv",
    2024: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2024.csv",
    2025: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2025.csv",
    2026: "https://raw.githubusercontent.com/marcosjantsch/shapefile-viewer/main/DadosOnline/resumo_2026.csv",
   
    }

def load_urls():
    logger.info("URLs de CSV carregadas de config_urls.py.")
    return CSV_URLS

def get_url_by_year(urls_dict, year: int):
    return urls_dict.get(int(year))
