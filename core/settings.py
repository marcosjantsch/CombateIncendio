from pathlib import Path
import os

from core.config import (
    detect_environment,
    earth_engine_project,
    get_environment_profile,
    load_project_from_auth_config,
    resolve_auth_config_path,
    resolve_geo_path,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = Path(os.getenv("APP_BASE_DIR", Path.cwd())).resolve()

if not (
    (BASE_DIR / "Data").exists()
    or (BASE_DIR / "data").exists()
    or (BASE_DIR / "DadosOnline").exists()
    or os.getenv("APP_GEO_PATH")
):
    BASE_DIR = PROJECT_DIR

ROOT_DIR = BASE_DIR
DATA_DIR = BASE_DIR / "Data"
DADOSONLINE_DIR = BASE_DIR / "DadosOnline"

APP_ENVIRONMENT = detect_environment(BASE_DIR)
APP_ENVIRONMENT_PROFILE = get_environment_profile(APP_ENVIRONMENT)
APP_ENVIRONMENT_DISPLAY_NAME = str(APP_ENVIRONMENT_PROFILE["display_name"])
APP_NAME = str(APP_ENVIRONMENT_PROFILE["app_name"])
DEFAULT_EE_PROJECT = str(APP_ENVIRONMENT_PROFILE["ee_project"])

AUTH_CONFIG_PATH = str(resolve_auth_config_path(BASE_DIR))
AUTH_CONFIG_PROJECT = load_project_from_auth_config(AUTH_CONFIG_PATH)
EE_PROJECT = earth_engine_project(DEFAULT_EE_PROJECT, AUTH_CONFIG_PROJECT)
if EE_PROJECT and not os.getenv("EE_PROJECT"):
    os.environ["EE_PROJECT"] = EE_PROJECT

APP_TITLE = "Visualizador de Shapefile e Dados Climáticos"
APP_ICON = "🗺️"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

SIMPLIFICATION_TOLERANCE = 0.001
MAX_FEATURES_FULL_MAP = 5000

GEO_PATH = str(resolve_geo_path(BASE_DIR))
LOGO_PATH = str((BASE_DIR / "assets" / "Logo.tif") if (BASE_DIR / "assets" / "Logo.tif").exists() else (PROJECT_DIR / "assets" / "Logo.tif"))

AUTH_ENABLED = (
    os.getenv("APP_AUTH_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
    and os.path.exists(AUTH_CONFIG_PATH)
)

TIPOS_DADO = [
    "Todos os Dados",
    "Dados por Estado",
    "Dados por Empresa",
    "Dados Empresa/Fazenda",
    "Dados por Município",
]

MESES_DISPONIVEIS = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4, "Mai": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Set": 9, "Out": 10, "Nov": 11, "Dez": 12
}

ANOS_DISPONIVEIS = list(range(2010, 2027))
