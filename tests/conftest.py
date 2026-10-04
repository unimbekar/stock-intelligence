import os

os.environ["DATA_MODE"] = "mock"
os.environ["ALERT_WATCH"] = "false"

from meridian_config.settings import get_settings  # noqa: E402

get_settings.cache_clear()
