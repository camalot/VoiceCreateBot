import os
import codecs
import yaml
from bot.cogs.lib import utils

class VoiceCreateMetricsConfig:
    def __init__(self, file: str):
        # set defaults for config from environment variables if they exist
        self.metrics = {
            "port": int(utils.dict_get(os.environ, "VCBE_CONFIG_METRICS_PORT", "8933")),
            "pollingInterval": int(utils.dict_get(os.environ, "VCBE_CONFIG_METRICS_POLLING_INTERVAL", "60")),
        }

        try:
            # check if file exists
            if os.path.exists(file):
                print(f"Loading config from {file}")
                with codecs.open(file, encoding="utf-8-sig", mode="r") as f:
                    settings = yaml.safe_load(f)
                    self.__dict__.update(settings)
        except yaml.YAMLError as exc:
            print(exc)
