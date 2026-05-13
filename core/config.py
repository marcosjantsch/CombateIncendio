from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from yaml.loader import SafeLoader


PROJECT_DIR = Path(__file__).resolve().parent.parent

ENVIRONMENT_PROFILES: dict[str, dict[str, Any]] = {
    "streamelit": {
        "aliases": {
            "streamelit",
            "streamlit",
            "stremelit",
            "stremlit",
            "coldroom",
            "cloudrun",
            "avant",
            "gfp",
            "gfpincendio",
        },
        "display_name": "GFP",
        "app_name": "Avant - Clima",
        "title": "Avant Plataforma de Auxilio de Combate a Incendios Florestais",
        "ee_project": "streamelit",
    },
    "braspine": {
        "aliases": {
            "braspine",
            "braspineincendio",
            "braspineincendio2",
        },
        "display_name": "Braspine",
        "app_name": "Braspine - Clima",
        "title": "Braspine Plataforma de Auxilio de Combate a Incendios Florestais",
        "ee_project": "braspine",
    },
}

ENVIRONMENT_SOURCE_VARS = (
    "APP_ENV",
    "GFP_ENV",
    "APP_PROFILE",
    "GFP_PROFILE",
    "CLIENT_ENV",
    "K_SERVICE",
    "K_CONFIGURATION",
    "K_REVISION",
    "CLOUD_RUN_SERVICE",
    "SERVICE_NAME",
)

GOOGLE_PROJECT_VARS = (
    "GOOGLE_CLOUD_PROJECT",
    "GCP_PROJECT",
    "GCLOUD_PROJECT",
)


def _env(env: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return env if env is not None else os.environ


def _normalize_candidate(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())


def normalize_environment(value: Any) -> str:
    candidate = _normalize_candidate(value)
    if not candidate:
        return ""

    for environment, profile in ENVIRONMENT_PROFILES.items():
        aliases = {
            _normalize_candidate(environment),
            *{
                _normalize_candidate(alias)
                for alias in profile.get("aliases", set())
            },
        }
        if candidate in aliases or any(alias and alias in candidate for alias in aliases):
            return environment

    return ""


def detect_environment(
    base_dir: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    env_values = _env(env)

    for var_name in ENVIRONMENT_SOURCE_VARS:
        environment = normalize_environment(env_values.get(var_name))
        if environment:
            return environment

    environment = normalize_environment(env_values.get("EE_PROJECT"))
    if environment:
        return environment

    for var_name in GOOGLE_PROJECT_VARS:
        environment = normalize_environment(env_values.get(var_name))
        if environment:
            return environment

    candidate_dirs = []
    if base_dir:
        candidate_dirs.append(Path(base_dir).name)
    candidate_dirs.append(PROJECT_DIR.name)

    for candidate in candidate_dirs:
        environment = normalize_environment(candidate)
        if environment:
            return environment

    return "streamelit"


def get_environment_profile(environment: str) -> dict[str, Any]:
    profile = ENVIRONMENT_PROFILES.get(environment) or ENVIRONMENT_PROFILES["streamelit"]
    return dict(profile)


def _path_from_value(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path


def resolve_auth_config_path(
    base_dir: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    env_values = _env(env)
    base_path = Path(base_dir or os.getenv("APP_BASE_DIR", Path.cwd())).resolve()

    explicit_path = str(env_values.get("APP_AUTH_CONFIG") or "").strip()
    if explicit_path:
        return _path_from_value(explicit_path, base_path)

    candidates = [
        base_path / "config.yaml",
        base_path / "auth" / "config.yaml",
        PROJECT_DIR / "config.yaml",
        PROJECT_DIR / "auth" / "config.yaml",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return base_path / "config.yaml"


def resolve_geo_path(
    base_dir: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> Path:
    env_values = _env(env)
    base_path = Path(base_dir or os.getenv("APP_BASE_DIR", Path.cwd())).resolve()

    explicit_path = str(env_values.get("APP_GEO_PATH") or "").strip()
    if explicit_path:
        return _path_from_value(explicit_path, base_path)

    candidates = [
        base_path / "Data" / "GEO.shp",
        base_path / "Data" / "Geo.shp",
        base_path / "data" / "Geo.shp",
        base_path / "data" / "GEO.shp",
        PROJECT_DIR / "Data" / "GEO.shp",
        PROJECT_DIR / "Data" / "Geo.shp",
        PROJECT_DIR / "data" / "Geo.shp",
        PROJECT_DIR / "data" / "GEO.shp",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return base_path / "Data" / "GEO.shp"


def load_project_from_auth_config(config_path: str | os.PathLike[str]) -> str:
    path = Path(config_path)
    if not path.exists():
        return ""

    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=SafeLoader) or {}
    except Exception:
        return ""

    if not isinstance(data, Mapping):
        return ""

    for key in ("project", "ee_project", "earth_engine_project"):
        value = data.get(key)
        if value:
            return str(value).strip()

    earth_engine = data.get("earth_engine")
    if isinstance(earth_engine, Mapping) and earth_engine.get("project"):
        return str(earth_engine.get("project")).strip()

    return ""


def earth_engine_project(
    default_project: str = "",
    settings_project: str = "",
    env: Mapping[str, str] | None = None,
) -> str:
    env_values = _env(env)
    project = (
        str(env_values.get("EE_PROJECT") or "").strip()
        or str(default_project or "").strip()
        or str(settings_project or "").strip()
    )

    if project:
        return project

    for var_name in GOOGLE_PROJECT_VARS:
        project = str(env_values.get(var_name) or "").strip()
        if project:
            return project

    return ""
