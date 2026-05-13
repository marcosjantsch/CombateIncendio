import altair as alt
import requests
import pandas as pd
import streamlit as st

from core.theme_palette import get_theme_palette
from services.log_service import log_error_once, log_success_once, log_warning_once


FORECAST_DAYS_DEFAULT = 16
WMO_HELP = (
    "Código padronizado da Organização Meteorológica Mundial (WMO) usado para "
    "representar a condição do tempo prevista, como céu limpo, chuva, nevoeiro ou trovoada."
)
def render_tab_previsao(
    gdf_filtered,
    selected_empresa=None,
    selected_fazenda=None,
    selected_municipio=None,
    selected_uf=None,
    logo_path=None,
    filters_version: int = 0,
):
    palette = get_theme_palette()
    chart_bg = palette["chart_surface"]
    axis_grid = palette["chart_grid"]
    axis_domain = palette["chart_domain"]
    axis_text = palette["chart_text"]
    precip_color = palette["chart_precip"]

    st.markdown('<div class="section-title">Previsão do Tempo</div>', unsafe_allow_html=True)

    if gdf_filtered is None or gdf_filtered.empty:
        log_warning_once(
            "tab_previsao",
            "empty_geometry",
            "Aba Previsao do Tempo sem geometria filtrada",
            {},
            signature={"empty": True, "filters_version": int(filters_version or 0)},
        )
        st.warning("⚠️ Não há geometria filtrada para calcular o centróide.")
        return

    geom = _build_target_geometry(gdf_filtered)
    if geom is None or geom.is_empty:
        log_error_once(
            "tab_previsao",
            "invalid_geometry",
            "Nao foi possivel obter a geometria da area selecionada para previsao",
            {"records": int(len(gdf_filtered))},
            signature={
                "records": int(len(gdf_filtered)),
                "invalid_geometry": True,
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("❌ Não foi possível obter a geometria da área selecionada.")
        return

    centroid = geom.centroid
    lat = float(centroid.y)
    lon = float(centroid.x)

    titulo_local = _descricao_local(
        selected_empresa=selected_empresa,
        selected_fazenda=selected_fazenda,
        selected_municipio=selected_municipio,
        selected_uf=selected_uf,
    )

    st.caption(f"Consulta por centróide | Latitude: {lat:.6f} | Longitude: {lon:.6f}")

    with st.expander("Fonte dos dados", expanded=False):
        st.markdown(
            f"""
**Origem:** Open-Meteo  
**Tipo de consulta:** API por coordenadas geográficas  
**Área consultada:** centróide da geometria filtrada  
**Latitude:** `{lat:.6f}`  
**Longitude:** `{lon:.6f}`  

**Fonte principal:**  
Open-Meteo Forecast API

**Variáveis consultadas:**  
- Código meteorológico
- Temperatura máxima diária
- Temperatura mínima diária
- Precipitação acumulada diária
- Probabilidade máxima de precipitação
- Velocidade máxima do vento

**Observação:**  
Esta seção permanece oculta por padrão e pode ser expandida quando o usuário desejar consultar a referência e os detalhes técnicos da previsão.
"""
        )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption(f"Horizonte da previsão: {FORECAST_DAYS_DEFAULT} dias")
    with col2:
        exibir_tabela = st.checkbox(
            "Exibir tabela completa",
            value=True,
            key="previsao_exibir_tabela",
        )

    data = _fetch_open_meteo_forecast(
        lat=lat,
        lon=lon,
        forecast_days=FORECAST_DAYS_DEFAULT,
    )

    if not data:
        log_error_once(
            "tab_previsao",
            "forecast_request_failed",
            "Consulta de previsao falhou no provedor remoto",
            {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "forecast_days": FORECAST_DAYS_DEFAULT,
            },
            signature={
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "forecast_days": FORECAST_DAYS_DEFAULT,
                "status": "request_failed",
                "filters_version": int(filters_version or 0),
            },
        )
        st.error("❌ Não foi possível consultar a previsão do tempo.")
        return

    df_previsao = _forecast_json_to_dataframe(data)
    if df_previsao.empty:
        log_warning_once(
            "tab_previsao",
            "forecast_empty",
            "Consulta de previsao retornou sem dados utilizaveis",
            {
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "forecast_days": FORECAST_DAYS_DEFAULT,
            },
            signature={
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "forecast_days": FORECAST_DAYS_DEFAULT,
                "status": "empty",
                "filters_version": int(filters_version or 0),
            },
        )
        st.warning("⚠️ A consulta foi realizada, mas não retornou dados utilizáveis.")
        return

    log_success_once(
        "tab_previsao",
        "forecast_ready",
        "Previsao do tempo preparada com sucesso",
        {
            "records": int(len(df_previsao)),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
        },
        signature={
            "records": int(len(df_previsao)),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "filters_version": int(filters_version or 0),
        },
    )

    st.markdown(f"### {titulo_local}")

    hoje = df_previsao.iloc[0].copy()
    amanha = df_previsao.iloc[1].copy() if len(df_previsao) > 1 else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hoje - Temp. Máx.", _fmt_val(hoje.get("temp_max"), "°C"))
    c2.metric("Hoje - Temp. Mín.", _fmt_val(hoje.get("temp_min"), "°C"))
    c3.metric("Hoje - Chuva", _fmt_val(hoje.get("precip_mm"), "mm"))
    c4.metric("Hoje - Prob. chuva", _fmt_val(hoje.get("precip_prob"), "%"))

    c5, c6, c7 = st.columns(3)
    c5.metric("Vento Máx.", _fmt_val(hoje.get("wind_max"), "km/h"))
    c6.metric(
        "Código WMO",
        str(int(hoje["weather_code"])) if pd.notna(hoje.get("weather_code")) else "N/A",
        help=WMO_HELP,
    )
    c7.metric("Condição", str(hoje.get("weather_desc", "N/A")))

    if amanha is not None:
        st.markdown("#### Amanhã")
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Amanhã - Temp. Máx.", _fmt_val(amanha.get("temp_max"), "°C"))
        a2.metric("Amanhã - Temp. Mín.", _fmt_val(amanha.get("temp_min"), "°C"))
        a3.metric("Amanhã - Chuva", _fmt_val(amanha.get("precip_mm"), "mm"))
        a4.metric("Amanhã - Prob. chuva", _fmt_val(amanha.get("precip_prob"), "%"))

        a5, a6, a7 = st.columns(3)
        a5.metric("Amanhã - Vento Máx.", _fmt_val(amanha.get("wind_max"), "km/h"))
        a6.metric(
            "Amanhã - Código WMO",
            str(int(amanha["weather_code"])) if pd.notna(amanha.get("weather_code")) else "N/A",
            help=WMO_HELP,
        )
        a7.metric("Amanhã - Condição", str(amanha.get("weather_desc", "N/A")))

    st.markdown("---")
    st.markdown("#### Gráficos")

    graf_col1, graf_col2 = st.columns(2)

    with graf_col1:
        base_temp = df_previsao.copy()
        base_temp["data_plot"] = pd.to_datetime(
            base_temp["data"], format="%d/%m/%Y", errors="coerce"
        )
        base_temp = base_temp.sort_values("data_plot", ascending=True)
        base_temp = base_temp.rename(
            columns={"temp_max": "Temperatura máxima", "temp_min": "Temperatura mínima"}
        )
        base_temp = base_temp.melt(
            id_vars=["data_plot"],
            value_vars=["Temperatura máxima", "Temperatura mínima"],
            var_name="Série",
            value_name="Temperatura",
        )
        chart_temp = (
            alt.Chart(base_temp)
            .mark_line(point=True, strokeWidth=2.5)
            .encode(
                x=alt.X(
                    "data_plot:T",
                    sort="ascending",
                    axis=alt.Axis(title=None, format="%d/%m", labelAngle=0),
                ),
                y=alt.Y("Temperatura:Q", title=None),
                color=alt.Color(
                    "Série:N",
                    title=None,
                    scale=alt.Scale(
                        domain=["Temperatura máxima", "Temperatura mínima"],
                        range=[palette["chart_temp_max"], palette["chart_temp_min"]],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("data_plot:T", title="Data", format="%d/%m/%Y"),
                    alt.Tooltip("Série:N", title="Série"),
                    alt.Tooltip("Temperatura:Q", title="Valor", format=".1f"),
                ],
            )
            .properties(height=300)
            .configure_view(
                stroke=palette["panel_border"],
                strokeOpacity=0.28,
                fill=chart_bg,
            )
            .configure_axis(
                gridColor=axis_grid,
                domainColor=axis_domain,
                tickColor=axis_domain,
                labelColor=axis_text,
                titleColor=axis_text,
            )
            .configure_legend(
                labelColor=axis_text,
                titleColor=axis_text,
                orient="top",
            )
        )
        st.altair_chart(chart_temp, use_container_width=True)

    with graf_col2:
        base_precip = df_previsao.copy()
        base_precip["data_plot"] = pd.to_datetime(
            base_precip["data"], format="%d/%m/%Y", errors="coerce"
        )
        base_precip = base_precip.sort_values("data_plot", ascending=True)
        base_precip = base_precip.rename(
            columns={"precip_mm": "Precipitação acumulada"}
        )
        chart_precip = (
            alt.Chart(base_precip)
            .mark_bar(color=precip_color)
            .encode(
                x=alt.X(
                    "data_plot:T",
                    sort="ascending",
                    axis=alt.Axis(title=None, format="%d/%m", labelAngle=0),
                ),
                y=alt.Y("Precipitação acumulada:Q", title=None),
                tooltip=[
                    alt.Tooltip("data_plot:T", title="Data", format="%d/%m/%Y"),
                    alt.Tooltip(
                        "Precipitação acumulada:Q",
                        title="Precipitação acumulada",
                        format=".1f",
                    ),
                ],
            )
            .properties(height=300)
            .configure_view(
                stroke=palette["panel_border"],
                strokeOpacity=0.28,
                fill=chart_bg,
            )
            .configure_axis(
                gridColor=axis_grid,
                domainColor=axis_domain,
                tickColor=axis_domain,
                labelColor=axis_text,
                titleColor=axis_text,
            )
        )
        st.altair_chart(chart_precip, use_container_width=True)

    st.markdown("---")
    st.markdown("#### Interpretação automática")
    st.info(_gerar_interpretacao(df_previsao))

    if exibir_tabela:
        st.markdown("---")
        st.markdown("#### Tabela de previsão")

        df_exibir = df_previsao[
            [
                "data",
                "weather_desc",
                "temp_max",
                "temp_min",
                "precip_mm",
                "precip_prob",
                "wind_max",
            ]
        ].copy()

        df_exibir = df_exibir.rename(
            columns={
                "data": "Data",
                "weather_desc": "Condição",
                "temp_max": "Temp. Máx. (°C)",
                "temp_min": "Temp. Mín. (°C)",
                "precip_mm": "Precipitação (mm)",
                "precip_prob": "Prob. Chuva (%)",
                "wind_max": "Vento Máx. (km/h)",
            }
        )

        st.dataframe(df_exibir, width="stretch", height=360)

    if logo_path:
        st.markdown("---")
        st.image(logo_path, width=180)
def _build_target_geometry(gdf):
    try:
        return gdf.geometry.union_all()
    except Exception:
        try:
            return gdf.unary_union
        except Exception:
            return None


def _descricao_local(
    selected_empresa=None,
    selected_fazenda=None,
    selected_municipio=None,
    selected_uf=None,
):
    if selected_empresa and selected_fazenda:
        return f"Previsão para {selected_empresa} | {selected_fazenda}"
    if selected_empresa:
        return f"Previsão para {selected_empresa}"
    if selected_municipio and selected_uf:
        return f"Previsão para {selected_municipio}/{selected_uf}"
    if selected_municipio:
        return f"Previsão para {selected_municipio}"
    return "Previsão da área selecionada"


@st.cache_data(show_spinner=False, ttl=1800)
def _fetch_open_meteo_forecast(
    lat: float,
    lon: float,
    forecast_days: int = FORECAST_DAYS_DEFAULT,
):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ",".join(
            [
                "weather_code",
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
            ]
        ),
        "timezone": "auto",
        "forecast_days": forecast_days,
    }

    try:
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def _forecast_json_to_dataframe(data: dict) -> pd.DataFrame:
    daily = data.get("daily", {})
    if not daily:
        return pd.DataFrame()

    df = pd.DataFrame(
        {
            "data": pd.to_datetime(daily.get("time", []), errors="coerce"),
            "weather_code": daily.get("weather_code", []),
            "temp_max": daily.get("temperature_2m_max", []),
            "temp_min": daily.get("temperature_2m_min", []),
            "precip_mm": daily.get("precipitation_sum", []),
            "precip_prob": daily.get("precipitation_probability_max", []),
            "wind_max": daily.get("wind_speed_10m_max", []),
        }
    )

    if df.empty:
        return df

    df["weather_desc"] = df["weather_code"].apply(_wmo_description)
    df["data"] = pd.to_datetime(df["data"], errors="coerce").dt.strftime("%d/%m/%Y")

    for col in ["temp_max", "temp_min", "precip_mm", "precip_prob", "wind_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(1)

    return df


def _wmo_description(code):
    mapa = {
        0: "Céu limpo",
        1: "Predominantemente limpo",
        2: "Parcialmente nublado",
        3: "Encoberto",
        45: "Nevoeiro",
        48: "Nevoeiro com geada",
        51: "Chuvisco fraco",
        53: "Chuvisco moderado",
        55: "Chuvisco forte",
        56: "Chuvisco gelado fraco",
        57: "Chuvisco gelado forte",
        61: "Chuva fraca",
        63: "Chuva moderada",
        65: "Chuva forte",
        66: "Chuva gelada fraca",
        67: "Chuva gelada forte",
        71: "Neve fraca",
        73: "Neve moderada",
        75: "Neve forte",
        77: "Grãos de neve",
        80: "Pancadas fracas",
        81: "Pancadas moderadas",
        82: "Pancadas fortes",
        85: "Pancadas de neve fracas",
        86: "Pancadas de neve fortes",
        95: "Trovoada",
        96: "Trovoada com granizo fraco",
        99: "Trovoada com granizo forte",
    }
    try:
        return mapa.get(int(code), "Condição não mapeada")
    except Exception:
        return "Condição não mapeada"


def _gerar_interpretacao(df: pd.DataFrame) -> str:
    if df.empty:
        return "Sem dados para interpretação."

    precip_total = pd.to_numeric(df["precip_mm"], errors="coerce").sum(skipna=True)
    dias_sem_chuva = int(
        (pd.to_numeric(df["precip_mm"], errors="coerce").fillna(0) < 1.0).sum()
    )
    temp_max_media = pd.to_numeric(df["temp_max"], errors="coerce").mean(skipna=True)
    vento_max = pd.to_numeric(df["wind_max"], errors="coerce").max(skipna=True)
    data_inicio = df["data"].iloc[0] if "data" in df.columns and not df.empty else None
    data_fim = df["data"].iloc[-1] if "data" in df.columns and not df.empty else None

    partes = []
    if data_inicio and data_fim:
        partes.append(
            f"Período analisado: de {data_inicio} até {data_fim}."
        )
    partes.append(f"Precipitação acumulada prevista no período: {precip_total:.1f} mm.")

    if dias_sem_chuva >= max(3, int(len(df) * 0.6)):
        partes.append("Há sinal de período predominantemente seco nos próximos dias.")
    else:
        partes.append("Há indicação de chuva em parte relevante do período.")

    if pd.notna(temp_max_media):
        partes.append(f"A temperatura máxima média prevista é de {temp_max_media:.1f} °C.")

    if pd.notna(vento_max) and vento_max >= 30:
        partes.append("Há pelo menos um dia com vento mais forte, exigindo atenção operacional.")
    else:
        partes.append("Não há destaque de vento extremo no horizonte consultado.")

    return " ".join(partes)


def _fmt_val(v, sufixo=""):
    if pd.isna(v):
        return "N/A"
    return f"{v:.1f} {sufixo}".strip()

