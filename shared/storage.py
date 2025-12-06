import json
from pathlib import Path

from .models import UserRecord

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
USER_FILE = DATA_DIR / "user_data.json"
APPSETTINGS_FILE = DATA_DIR / "appsettings.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_users() -> dict[str, UserRecord]:
    ensure_data_dir()
    if USER_FILE.exists():
        with USER_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("users", {})
        return {
            k: UserRecord(
                userid=k,
                password=v.get("password", ""),
                user_nickname=(v.get("user_nickname") or v.get("user_name") or ""),
                user_realname=v.get("user_realname"),
                head_img=v.get("head_img", ""),
                pt_timestamp=v.get("pt_timestamp"),
            )
            for k, v in raw.items()
        }
    return {}


def save_users(users: dict[str, UserRecord]) -> None:
    ensure_data_dir()
    payload = {
        "users": {
            u.userid: {
                "password": u.password,
                "user_nickname": u.user_nickname,
                "user_realname": u.user_realname,
                "head_img": u.head_img,
                "pt_timestamp": u.pt_timestamp,
            }
            for u in users.values()
        }
    }
    with USER_FILE.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_appsettings() -> dict:
    ensure_data_dir()
    if APPSETTINGS_FILE.exists():
        with APPSETTINGS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    default = {"port": 24300}
    with APPSETTINGS_FILE.open("w", encoding="utf-8") as f:
        json.dump(default, f, ensure_ascii=False, indent=2)
    return default
