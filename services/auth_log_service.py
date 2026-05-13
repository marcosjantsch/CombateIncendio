# services/auth_log_service.py
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


LOG_FILE = Path("auth_login_log.csv")


def _ensure_log_file() -> None:
    if not LOG_FILE.exists():
        with LOG_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "username",
                "nome",
                "perfil",
                "login_data_hora",
                "logout_data_hora",
                "status",
            ])


def registrar_login(username: str, nome: str = "", perfil: str = "") -> None:
    _ensure_log_file()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            username or "",
            nome or "",
            perfil or "",
            agora,
            "",
            "LOGIN",
        ])


def registrar_logout(username: str, nome: str = "", perfil: str = "") -> None:
    _ensure_log_file()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            username or "",
            nome or "",
            perfil or "",
            "",
            agora,
            "LOGOUT",
        ])