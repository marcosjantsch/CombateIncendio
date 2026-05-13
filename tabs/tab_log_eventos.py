# tabs/tab_log_eventos.py
from __future__ import annotations

import json

import streamlit as st

from services.log_service import clear_logs, get_logs, logs_to_dataframe, log_info


def render_tab_log_eventos() -> None:
    log_info("tab_log_eventos", "Aba de log renderizada", {"aba": "Log de eventos"})

    st.subheader("Log de eventos")

    c1, c2, c3 = st.columns([1, 1, 3])

    with c1:
        if st.button("Atualizar log", width="stretch"):
            log_info("tab_log_eventos", "Botão Atualizar log acionado")
            st.rerun()

    with c2:
        if st.button("Limpar log", width="stretch"):
            clear_logs()
            log_info("tab_log_eventos", "Log limpo pelo usuário")
            st.rerun()

    logs = get_logs()
    df_logs = logs_to_dataframe()

    st.caption(f"Total de eventos registrados: {len(logs)}")

    with st.expander("Session State", expanded=False):
        st.write(st.session_state)

    if df_logs.empty:
        st.info("Nenhum evento registrado até o momento.")
        return

    with st.expander("Tabela de log", expanded=True):
        st.dataframe(df_logs, width="stretch", hide_index=True)

    with st.expander("Detalhamento dos eventos", expanded=False):
        for item in reversed(logs):
            titulo = (
                f"{item.get('timestamp', '')} | "
                f"{item.get('level', '')} | "
                f"{item.get('source', '')} | "
                f"{item.get('message', '')}"
            )

            with st.expander(titulo, expanded=False):
                details = item.get("details", {}) or {}
                if details:
                    st.code(
                        json.dumps(details, ensure_ascii=False, indent=2, default=str),
                        language="json",
                    )
                else:
                    st.write("Sem detalhes adicionais.")
