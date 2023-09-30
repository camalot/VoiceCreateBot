import os
import codecs
import inspect
import traceback
import yaml

from bot.cogs.lib import utils
from bot.cogs.lib.logger import Log
from bot.cogs.lib.loglevel import LogLevel
from bot.cogs.lib.settings import Settings

class VoiceCreateMetricsConfig:
    def __init__(self, file: str):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = Log(log_level)

        # set defaults for config from environment variables if they exist
        self.metrics = {
            "port": int(utils.dict_get(os.environ, "VCBE_CONFIG_METRICS_PORT", "8933")),
            "pollingInterval": int(utils.dict_get(os.environ, "VCBE_CONFIG_METRICS_POLLING_INTERVAL", "60")),
        }

        # load config from file
        try:
            # check if file exists
            if os.path.exists(file):
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Loading config from {file}")
                with codecs.open(file, encoding="utf-8-sig", mode="r") as f:
                    settings = yaml.safe_load(f)
                    self.__dict__.update(settings)
        except yaml.YAMLError as exc:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(exc), traceback.format_exc())
