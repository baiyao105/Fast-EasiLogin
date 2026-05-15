from __future__ import annotations

import contextlib
import tomllib
from pathlib import Path

import tomlkit
from loguru import logger

from fast_easilogin.shared.basic_dir import APPSETTINGS_FILE, APPSETTINGS_TOML, DATA_DIR, atomic_write
from fast_easilogin.shared.store.models import CURRENT_SCHEMA_VERSION, AppSettings

toml_dumps = tomlkit.dumps


class AppSettingsManager:
    def __init__(self, toml_path: Path | None = None, legacy_json_path: Path | None = None):
        self.toml_path = toml_path or APPSETTINGS_TOML
        self.legacy_json_path = legacy_json_path or APPSETTINGS_FILE
        self._cached: AppSettings | None = None
        self._cache_mtime: float = 0.0

    def _load_toml(self) -> dict:
        p = self.toml_path
        if not p.exists():
            return {}
        try:
            raw = p.read_bytes()
            return tomllib.loads(raw.decode("utf-8"))
        except Exception as err:
            logger.error("读取 TOML 失败: path={} err={}", str(p), str(err))
            return {}

    def _merge(self, file_cfg: dict) -> dict:
        defaults = AppSettings().model_dump()
        merged = defaults.copy()
        fc = dict(file_cfg or {})
        if isinstance(fc.get("Global"), dict):
            merged["Global"].update(fc.get("Global") or {})
        for k, v in fc.items():
            if k not in ("Global",):
                merged[k] = v
        merged["schema_version"] = CURRENT_SCHEMA_VERSION
        return merged

    def _validate(self, cfg: dict) -> AppSettings:
        try:
            return AppSettings.model_validate(cfg)
        except Exception as err:
            logger.error("配置校验失败: {}", str(err))
            raise

    def _current_mtime(self) -> float:
        if self.toml_path.exists():
            with contextlib.suppress(OSError):
                return self.toml_path.stat().st_mtime
        return 0.0

    def write(self, cfg: dict) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        text = toml_dumps(cfg)
        atomic_write(self.toml_path, text)
        self._cached = None

    def load(self) -> AppSettings:
        mtime = self._current_mtime()
        if self._cached is not None and self._cache_mtime == mtime:
            return self._cached
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        file_cfg = self._load_toml()
        if not file_cfg:
            merged = self._merge({})
            try:
                self.write(merged)
            except Exception as err:
                logger.error("写入 TOML 失败: err={}", str(err))
            file_cfg = merged
        cfg = self._merge(file_cfg)
        app_settings = self._validate(cfg)
        self._cached = app_settings
        self._cache_mtime = mtime
        return app_settings


_settings_manager: AppSettingsManager | None = None


def write_config(cfg: dict) -> None:
    AppSettingsManager().write(cfg)


def load_appsettings_model() -> AppSettings:
    global _settings_manager  # noqa: PLW0603
    if _settings_manager is None:
        _settings_manager = AppSettingsManager()
    return _settings_manager.load()


def load_appsettings() -> dict:
    return load_appsettings_model().model_dump()
