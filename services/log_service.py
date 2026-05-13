# services/log_service.py
from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


LOG_SESSION_KEY = "event_log_records"
LOG_INIT_KEY = "event_log_initialized"
LOG_SEQ_KEY = "event_log_sequence"
LOG_META_KEY = "event_log_meta"
LOG_DEDUP_KEY = "event_log_dedup"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_log_store() -> List[Dict[str, Any]]:
    if LOG_SESSION_KEY not in st.session_state:
        st.session_state[LOG_SESSION_KEY] = []
    if LOG_SEQ_KEY not in st.session_state:
        st.session_state[LOG_SEQ_KEY] = 0
    if LOG_META_KEY not in st.session_state:
        st.session_state[LOG_META_KEY] = {}
    if LOG_DEDUP_KEY not in st.session_state:
        st.session_state[LOG_DEDUP_KEY] = {}
    return st.session_state[LOG_SESSION_KEY]


def _next_sequence() -> int:
    _ensure_log_store()
    st.session_state[LOG_SEQ_KEY] = int(st.session_state.get(LOG_SEQ_KEY, 0)) + 1
    return st.session_state[LOG_SEQ_KEY]


def initialize_logs(app_name: str, version: str) -> None:
    current_meta = dict(st.session_state.get(LOG_META_KEY, {}))
    if (
        st.session_state.get(LOG_INIT_KEY)
        and current_meta.get("app_name") == app_name
        and current_meta.get("version") == version
    ):
        return

    st.session_state[LOG_SESSION_KEY] = []
    st.session_state[LOG_SEQ_KEY] = 0
    st.session_state[LOG_DEDUP_KEY] = {}
    st.session_state[LOG_META_KEY] = {
        "app_name": app_name,
        "version": version,
        "started_at": _now_iso(),
    }
    st.session_state[LOG_INIT_KEY] = True

    add_log(
        "INFO",
        "app",
        "Sessão de log iniciada",
        {
            "app_name": app_name,
            "version": version,
            "started_at": st.session_state[LOG_META_KEY]["started_at"],
        },
    )


def restart_logs(
    app_name: Optional[str] = None,
    version: Optional[str] = None,
    reason: str = "Sessao de log reiniciada",
) -> None:
    current_meta = dict(st.session_state.get(LOG_META_KEY, {}))
    target_app = app_name or str(current_meta.get("app_name") or "Avant")
    target_version = version or str(current_meta.get("version") or "")

    st.session_state[LOG_INIT_KEY] = False
    initialize_logs(target_app, target_version)

    if reason:
        add_log(
            "INFO",
            "log_service",
            reason,
            {"app_name": target_app, "version": target_version},
        )


def clear_logs(reason: str = "Log reiniciado") -> None:
    st.session_state[LOG_SESSION_KEY] = []
    st.session_state[LOG_SEQ_KEY] = 0
    st.session_state[LOG_DEDUP_KEY] = {}

    meta = dict(st.session_state.get(LOG_META_KEY, {}))
    if meta:
        meta["started_at"] = _now_iso()
        st.session_state[LOG_META_KEY] = meta

    add_log("INFO", "log_service", reason, {"action": "clear_logs"})


def add_log(
    level: str,
    source: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    store = _ensure_log_store()
    normalized_details = details if isinstance(details, dict) else {"details": details}

    store.append(
        {
            "sequence": _next_sequence(),
            "timestamp": _now_iso(),
            "level": str(level).upper(),
            "source": str(source),
            "message": str(message),
            "details": normalized_details or {},
        }
    )


def log_once(
    level: str,
    source: str,
    key: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    signature: Any = None,
) -> bool:
    _ensure_log_store()
    dedup_store = st.session_state[LOG_DEDUP_KEY]
    normalized_key = f"{source}:{key}"
    normalized_signature = json.dumps(signature, ensure_ascii=False, default=str, sort_keys=True)

    if dedup_store.get(normalized_key) == normalized_signature:
        return False

    dedup_store[normalized_key] = normalized_signature
    add_log(level=level, source=source, message=message, details=details)
    return True


def log_info(source: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    add_log("INFO", source, message, details)


def log_warning(source: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    add_log("WARNING", source, message, details)


def log_error(source: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    add_log("ERROR", source, message, details)


def log_success(source: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    add_log("SUCCESS", source, message, details)


def log_info_once(
    source: str,
    key: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    signature: Any = None,
) -> bool:
    return log_once("INFO", source, key, message, details=details, signature=signature)


def log_warning_once(
    source: str,
    key: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    signature: Any = None,
) -> bool:
    return log_once("WARNING", source, key, message, details=details, signature=signature)


def log_error_once(
    source: str,
    key: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    signature: Any = None,
) -> bool:
    return log_once("ERROR", source, key, message, details=details, signature=signature)


def log_success_once(
    source: str,
    key: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    signature: Any = None,
) -> bool:
    return log_once("SUCCESS", source, key, message, details=details, signature=signature)


def get_logs() -> List[Dict[str, Any]]:
    return list(_ensure_log_store())


def get_log_metadata() -> Dict[str, Any]:
    _ensure_log_store()
    return dict(st.session_state.get(LOG_META_KEY, {}))


def logs_to_dataframe() -> pd.DataFrame:
    rows = []
    for item in _ensure_log_store():
        base = {
            "sequence": item.get("sequence"),
            "timestamp": item.get("timestamp"),
            "level": item.get("level"),
            "source": item.get("source"),
            "message": item.get("message"),
        }
        details = item.get("details", {}) or {}
        if not isinstance(details, dict):
            details = {"details": str(details)}

        row = {
            **base,
            **details,
            "details_json": json.dumps(details, ensure_ascii=False, default=str),
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame(
            columns=["sequence", "timestamp", "level", "source", "message", "details_json"]
        )

    return pd.DataFrame(rows)


def export_logs_csv_bytes() -> bytes:
    df = logs_to_dataframe()
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    return buffer.getvalue().encode("utf-8-sig")


def export_logs_json_bytes() -> bytes:
    payload = {
        "metadata": get_log_metadata(),
        "records": get_logs(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def get_log_download_filename(prefix: str = "avant_event_log") -> str:
    meta = get_log_metadata()
    started_at = str(meta.get("started_at", _now_iso())).replace(":", "-")
    return f"{prefix}_{started_at}.csv"
