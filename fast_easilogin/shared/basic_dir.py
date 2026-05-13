from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
USER_FILE = DATA_DIR / "user_data.json"
APPSETTINGS_FILE = DATA_DIR / "appsettings.json"
APPSETTINGS_TOML = DATA_DIR / "appsettings.toml"
USER_DATA_DIR = DATA_DIR / "user_data"
LOGS_DIR = DATA_DIR / "Logs"


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
