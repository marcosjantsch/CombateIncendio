from pathlib import Path
import os

PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = Path(os.getenv("APP_BASE_DIR", Path.cwd())).resolve()

if not (BASE_DIR / "Data").exists():
    BASE_DIR = PROJECT_DIR

ROOT_DIR = BASE_DIR
DATA_DIR = BASE_DIR / "Data"
DADOSONLINE_DIR = BASE_DIR / "DadosOnline"

APP_TITLE = "Visualizador de Shapefile e Dados Climáticos"
APP_ICON = "🗺️"
LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

SIMPLIFICATION_TOLERANCE = 0.001
MAX_FEATURES_FULL_MAP = 5000

GEO_PATH = str(DATA_DIR / "Geo.shp")
LOGO_PATH = str((BASE_DIR / "assets" / "Logo.tif") if (BASE_DIR / "assets" / "Logo.tif").exists() else (PROJECT_DIR / "assets" / "Logo.tif"))

AUTH_ENABLED = (
    os.getenv("APP_AUTH_ENABLED", "1").strip().lower() not in {"0", "false", "no"}
    and (os.path.exists(BASE_DIR / "config.yaml") or os.path.exists(PROJECT_DIR / "config.yaml"))
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
