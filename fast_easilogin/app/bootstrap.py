from loguru import logger

from fast_easilogin.app.utils import setup_logging
from fast_easilogin.core.basic_dir import ensure_data_dirs
from fast_easilogin.core.constants import APP_NAME


def bootstrap(log_level: str = "INFO") -> None:
    """初始化"""
    logger.info("Initializing {}...", APP_NAME)
    setup_logging(log_level)
    ensure_data_dirs()
    logger.success("Bootstrap completed")
