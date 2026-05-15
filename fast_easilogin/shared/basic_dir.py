import time
from pathlib import Path


def atomic_write(path: Path, data: str, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(data, encoding="utf-8")
            tmp.replace(path)
        except PermissionError:
            if attempt == max_retries - 1:
                raise
            time.sleep(0.1 * (attempt + 1))
        else:
            return


REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
USER_FILE = DATA_DIR / "user_data.json"
APPSETTINGS_FILE = DATA_DIR / "appsettings.json"
APPSETTINGS_TOML = DATA_DIR / "appsettings.toml"
USER_DATA_DIR = DATA_DIR / "user_data"
LOGS_DIR = DATA_DIR / "Logs"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
