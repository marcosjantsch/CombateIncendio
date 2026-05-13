from datetime import datetime
import streamlit as st
from services.log_service import log_error_once, log_success_once, log_warning_once


def render_tab_tendencia_climatica(
    gdf_filtered,
    selected_empresa=None,
    selected_fazenda=None,
    selected_municipio=None,
    selected_uf=None,
    logo_path=None,
    filters_version: int = 0,
):
    st.markdown('<div class="section-title">Tendência Climática</div>', unsafe_allow_html=True)

    if gdf_filtered is None or gdf_filtered.empty:
        log_warning_once(
            "tab_tendencia",
            "empty_geometry",
            "Aba Tendencia Climatica sem geometria filtrada",
            {},
            signature={"empty": True, "filters_version": int(filters_version or 0)},
        )
        st.warning("⚠️ Não há geometria filtrada para calcular o centróide.")
        return

    geom = _build_target_geometry(gdf_filtered)
    if geom is None or geom.is_empty:
        log_error_once(
            "tab_tendencia",
            "invalid_geometry",
            "Nao foi possivel obter a geometria da area selecionada para tendencia climatica",
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

    contexto = {
        "lat": lat,
        "lon": lon,
        "selected_empresa": selected_empresa,
        "selected_fazenda": selected_fazenda,
        "selected_municipio": selected_municipio,
        "selected_uf": selected_uf,
        "titulo_local": titulo_local,
        "nome_local": _nome_local_texto(
            selected_empresa=selected_empresa,
            selected_fazenda=selected_fazenda,
            selected_municipio=selected_municipio,
            selected_uf=selected_uf,
        ),
    }

    st.markdown(f"### {titulo_local}")
    st.caption(f"Consulta espacial baseada no centróide | Latitude: {lat:.6f} | Longitude: {lon:.6f}")

    with st.expander("Fonte dos dados", expanded=False):
        st.markdown(
            f"""
**Tipo de informação exibida:** tendência climática sazonal interpretativa  
**Área consultada:** centróide da geometria filtrada  
**Latitude:** `{lat:.6f}`  
**Longitude:** `{lon:.6f}`  

**Estrutura atual da aba:**  
Esta versão apresenta interpretação climática sazonal inicial baseada no contexto geográfico da área selecionada.

**Objetivo:**  
- apoiar planejamento florestal e operacional  
- destacar possibilidade de período mais seco ou mais úmido  
- sinalizar comportamento climático regional esperado  

**Observação importante:**  
O conteúdo exibido nesta aba deve ser interpretado como apoio ao planejamento,  
não como previsão diária determinística.
"""
        )

    dados_3_meses = _gerar_tendencia_3_meses(contexto)
    dados_6_meses = _gerar_tendencia_6_meses(contexto)

    log_success_once(
        "tab_tendencia",
        "trend_ready",
        "Tendencia climatica preparada com sucesso",
        {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "titulo_local": titulo_local,
        },
        signature={
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "titulo_local": titulo_local,
            "filters_version": int(filters_version or 0),
        },
    )

    st.markdown("---")
    st.markdown("#### Tendência Climática — Próximos 3 meses")
    _render_bloco_tendencia(
        titulo="Próximos 3 meses",
        texto=dados_3_meses["texto"],
        fonte=dados_3_meses["fonte"],
        data_referencia=dados_3_meses["data_referencia"],
        data_emissao=dados_3_meses["data_emissao"],
    )

    st.markdown("---")
    st.markdown("#### Tendência Climática — Próximos 6 meses")
    _render_bloco_tendencia(
        titulo="Próximos 6 meses",
        texto=dados_6_meses["texto"],
        fonte=dados_6_meses["fonte"],
        data_referencia=dados_6_meses["data_referencia"],
        data_emissao=dados_6_meses["data_emissao"],
    )

    st.markdown("---")
    st.markdown("#### Observação")
    st.caption(
        "A tendência climática apresentada nesta aba deve ser utilizada como suporte ao planejamento "
        "e interpretada em conjunto com a previsão do tempo de curto prazo."
    )

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
        return f"Tendência climática para {selected_empresa} | {selected_fazenda}"
    if selected_empresa:
        return f"Tendência climática para {selected_empresa}"
    if selected_municipio and selected_uf:
        return f"Tendência climática para {selected_municipio}/{selected_uf}"
    if selected_municipio:
        return f"Tendência climática para {selected_municipio}"
    return "Tendência climática da área selecionada"


def _nome_local_texto(
    selected_empresa=None,
    selected_fazenda=None,
    selected_municipio=None,
    selected_uf=None,
):
    if selected_empresa and selected_fazenda:
        return f"{selected_empresa} / {selected_fazenda}"
    if selected_empresa:
        return str(selected_empresa)
    if selected_municipio and selected_uf:
        return f"{selected_municipio}/{selected_uf}"
    if selected_municipio:
        return str(selected_municipio)
    return "a área selecionada"


def _classificar_regiao(lat, lon):
    if lat < -23:
        return "Sul"
    if lat < -15:
        return "Sudeste"
    if lat < -8:
        return "Centro-Oeste"
    if lat < -2:
        return "Nordeste"
    return "Norte"


def _gerar_icones_tendencia(texto: str) -> str:
    texto_lower = str(texto).lower()
    icones = []

    if any(
        p in texto_lower
        for p in [
            "seca",
            "estiagem",
            "déficit hídrico",
            "deficit hídrico",
            "mais seco",
            "período seco",
            "periodo seco",
            "restrição hídrica",
            "restricao hídrica",
            "estresse hídrico",
            "estresse hidrico",
        ]
    ):
        icones.append("🔥")

    if any(
        p in texto_lower
        for p in [
            "chuva",
            "chuvas",
            "precipitação",
            "precipitacao",
            "úmido",
            "umido",
            "úmidas",
            "umidas",
            "mais úmido",
            "mais umido",
        ]
    ):
        icones.append("🌧")

    if any(
        p in texto_lower
        for p in [
            "temperatura",
            "temperaturas",
            "calor",
            "acima da média",
            "acima da media",
            "temperaturas elevadas",
        ]
    ):
        icones.append("🌡")

    return " ".join(icones) if icones else "🌍"


def _render_bloco_tendencia(
    titulo: str,
    texto: str,
    fonte: str,
    data_referencia: str,
    data_emissao: str,
):
    icones = _gerar_icones_tendencia(texto)

    texto_html = str(texto).replace("\n", "<br><br>")
    fonte_html = str(fonte).replace("\n", "<br>")
    referencia_html = str(data_referencia).replace("\n", "<br>")
    emissao_html = str(data_emissao).replace("\n", "<br>")

    html = (
        f'<div style="background-color:#e8f5e9;'
        f'border-left:6px solid #2e7d32;'
        f'padding:18px 20px;'
        f'border-radius:10px;'
        f'margin-top:8px;'
        f'margin-bottom:8px;">'
        f'<div style="font-size:1.20rem;'
        f'font-weight:700;'
        f'color:#1b5e20;'
        f'margin-bottom:12px;">'
        f"{icones} {titulo}"
        f"</div>"
        f'<p style="font-size:1.10rem;'
        f'line-height:1.80;'
        f'color:#000000;'
        f'margin:0 0 14px 0;'
        f'text-align:justify;">'
        f"{texto_html}"
        f"</p>"
        f'<div style="font-size:0.96rem;'
        f'color:#000000;'
        f'border-top:1px solid #c8e6c9;'
        f'padding-top:10px;'
        f'line-height:1.65;">'
        f"<strong style=\"color:#000000;\">Fonte:</strong> <span style=\"color:#000000;\">{fonte_html}</span><br>"
        f"<strong style=\"color:#000000;\">Referência:</strong> <span style=\"color:#000000;\">{referencia_html}</span><br>"
        f"<strong style=\"color:#000000;\">Data da emissão/geração:</strong> <span style=\"color:#000000;\">{emissao_html}</span>"
        f"</div>"
        f"</div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def _data_execucao_formatada() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _periodo_referencia_meses(qtd_meses: int) -> str:
    agora = datetime.now()
    mes = agora.month
    ano = agora.year

    nomes = {
        1: "jan",
        2: "fev",
        3: "mar",
        4: "abr",
        5: "mai",
        6: "jun",
        7: "jul",
        8: "ago",
        9: "set",
        10: "out",
        11: "nov",
        12: "dez",
    }

    fim_mes = mes + qtd_meses - 1
    fim_ano = ano

    while fim_mes > 12:
        fim_mes -= 12
        fim_ano += 1

    return f"{nomes[mes]}/{ano} a {nomes[fim_mes]}/{fim_ano}"


def _gerar_tendencia_3_meses(contexto: dict) -> dict:
    nome_local = contexto.get("nome_local", "a área selecionada")
    lat = contexto.get("lat")
    lon = contexto.get("lon")
    regiao = _classificar_regiao(lat, lon)

    if regiao == "Sul":
        texto = (
            f"Para {nome_local}, os próximos 3 meses sugerem um comportamento mais irregular da chuva, "
            f"com alternância entre momentos de melhor umidade e intervalos de maior restrição hídrica. "
            f"Na prática, isso pode provocar oscilação na condição do solo, na trafegabilidade e no ritmo das operações. "
            f"Como orientação de curto horizonte, vale planejar as atividades com flexibilidade e acompanhar com atenção "
            f"a distribuição das chuvas, e não apenas o volume acumulado."
        )
    elif regiao == "Sudeste":
        texto = (
            f"Para {nome_local}, a tendência de 3 meses aponta para redução gradual das chuvas em parte do período, "
            f"com possibilidade de temperaturas mais elevadas. Esse sinal tende a aumentar a perda de umidade do solo, "
            f"favorecer a evolução de estiagem localizada e ampliar a sensibilidade das operações ao comportamento hídrico. "
            f"Do ponto de vista prático, convém reforçar o monitoramento da disponibilidade de água e revisar atividades "
            f"mais dependentes de condições estáveis de solo e clima."
        )
    elif regiao == "Centro-Oeste":
        texto = (
            f"Para {nome_local}, os próximos 3 meses tendem a manter um padrão mais seco, com menor frequência de chuva "
            f"e maior potencial de restrição hídrica entre eventos de precipitação. Esse cenário pode reduzir a recuperação "
            f"da umidade no solo e elevar a exposição das atividades de campo ao calor e ao déficit hídrico. "
            f"A leitura operacional recomenda vigilância reforçada sobre balanço hídrico, condições de campo "
            f"e janelas mais adequadas para execução."
        )
    elif regiao == "Nordeste":
        texto = (
            f"Para {nome_local}, o cenário de 3 meses indica persistência de irregularidade na distribuição das chuvas, "
            f"com possibilidade de acumulados abaixo do esperado em parte da janela analisada. Mesmo quando houver precipitação, "
            f"ela pode ocorrer de forma insuficiente para sustentar regularidade de umidade ao longo do período. "
            f"Isso reforça a necessidade de acompanhamento constante das condições regionais e atenção ao risco de estresse hídrico."
        )
    else:
        texto = (
            f"Para {nome_local}, os próximos 3 meses tendem a manter temperaturas elevadas, com presença de chuva, "
            f"mas com distribuição temporal potencialmente irregular. Esse comportamento pode gerar alternância entre momentos "
            f"de solo mais encharcado e intervalos de secagem rápida, exigindo leitura cuidadosa das condições locais. "
            f"Como apoio operacional, o mais importante é acompanhar a sequência dos eventos de chuva e seus reflexos "
            f"na umidade do solo e no acesso ao campo."
        )

    return {
        "texto": texto,
        "fonte": "Interpretação climática regional baseada em contexto geográfico da área selecionada",
        "data_referencia": f"Janela sazonal estimada: {_periodo_referencia_meses(3)}",
        "data_emissao": _data_execucao_formatada(),
    }


def _gerar_tendencia_6_meses(contexto: dict) -> dict:
    nome_local = contexto.get("nome_local", "a área selecionada")
    lat = contexto.get("lat")
    lon = contexto.get("lon")
    regiao = _classificar_regiao(lat, lon)

    if regiao == "Sul":
        texto = (
            f"Para {nome_local}, a leitura de 6 meses sugere continuidade de alta variabilidade climática, com alternância "
            f"entre fases mais úmidas e períodos de maior restrição hídrica. Em um horizonte mais estratégico, isso indica "
            f"que o planejamento deve trabalhar com cenários e não com uma condição única predominante. "
            f"A recomendação é manter flexibilidade nas janelas operacionais e revisar prioridades conforme a evolução real da chuva e da umidade."
        )
    elif regiao == "Sudeste":
        texto = (
            f"Para {nome_local}, o horizonte de 6 meses sugere consolidação de uma fase mais seca em parte do ciclo, "
            f"seguida por transição gradual para condições menos restritivas. Se as temperaturas permanecerem elevadas, "
            f"o déficit hídrico pode se intensificar em determinados momentos e pressionar áreas mais sensíveis. "
            f"Em termos estratégicos, essa leitura ajuda a antecipar prioridades de monitoramento, organização de recursos "
            f"e definição das janelas mais seguras para operações dependentes de condição climática."
        )
    elif regiao == "Centro-Oeste":
        texto = (
            f"Para {nome_local}, a tendência de 6 meses indica sazonalidade bem marcada, com uma fase seca mais definida "
            f"antes da retomada gradual das chuvas. Esse padrão favorece acúmulo de estresse hídrico ao longo do ciclo "
            f"e exige organização antecipada das atividades mais sensíveis ao ambiente seco. "
            f"A leitura estratégica recomenda atenção elevada ao balanço hídrico, ao risco operacional e ao planejamento "
            f"das janelas de campo com maior previsibilidade."
        )
    elif regiao == "Nordeste":
        texto = (
            f"Para {nome_local}, o horizonte de 6 meses aponta para continuidade da irregularidade das chuvas, com chance "
            f"de intervalos secos mais prolongados em parte da área. Nesse tipo de cenário, o principal ponto de atenção "
            f"não é apenas o total de precipitação, mas a capacidade de manter regularidade de umidade ao longo do tempo. "
            f"Essa condição reforça a necessidade de planejamento prudente, monitoramento constante e combinação desta leitura "
            f"com sinais de curto prazo e observação local."
        )
    else:
        texto = (
            f"Para {nome_local}, a leitura de 6 meses sugere persistência de temperaturas elevadas e comportamento variável "
            f"da precipitação, com possibilidade de redução em parte do horizonte analisado. Em termos estratégicos, "
            f"isso pede acompanhamento contínuo da sequência de chuva, da resposta da umidade do solo e das condições de acesso ao campo. "
            f"A recomendação é usar essa tendência como orientação de planejamento e refiná-la com previsão de curto prazo "
            f"e histórico climático da área."
        )

    return {
        "texto": texto,
        "fonte": "Interpretação climática regional baseada em contexto geográfico da área selecionada",
        "data_referencia": f"Janela sazonal estimada: {_periodo_referencia_meses(6)}",
        "data_emissao": _data_execucao_formatada(),
    }

