import inspect
import os
import time
import traceback

from prometheus_client import Gauge
from bot.cogs.lib.mongodb.exporter import ExporterMongoDatabase
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib import settings


class VoiceCreateMetrics:
    def __init__(self, config):
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        self.namespace = "voicecreate"
        self.polling_interval_seconds = config.metrics["pollingInterval"]
        self.config = config

        self.settings = settings.Settings()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG
        self.log = Log(minimumLogLevel=log_level)

        self.exporter_db = ExporterMongoDatabase()

        self.errors = Gauge(
            namespace=self.namespace,
            name=f"exporter_errors",
            documentation="The number of errors encountered",
            labelnames=["source"])

        self.guilds = Gauge(
            namespace=self.namespace,
            name=f"guild",
            documentation="The guilds that the bot is in",
            labelnames=["guild_id", "name"])

        self.user_settings = Gauge(
            namespace=self.namespace,
            name=f"user_settings",
            documentation="The number of user settings",
            labelnames=["guild_id"])

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Metrics initialized")


    def run_metrics_loop(self):
        """Metrics fetching loop"""
        _method = inspect.stack()[0][3]
        while True:
            try:
                self.log.info(0, f"{self._module}.{self._class}.{_method}", f"Begin metrics fetch")
                self.fetch()
                self.log.info(0, f"{self._module}.{self._class}.{_method}", f"End metrics fetch")
                self.log.debug(
                    0,
                    f"{self._module}.{self._class}.{_method}",
                    f"Sleeping for {self.polling_interval_seconds} seconds",
                )
                time.sleep(self.polling_interval_seconds)
            except Exception as ex:
                self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())

    def fetch(self):
        _method = inspect.stack()[0][3]
        known_guilds = []
        try:
            q_guilds = self.exporter_db.get_guilds() or []
            for row in q_guilds:
                known_guilds.append(row['guild_id'])
                self.guilds.labels(guild_id=row['guild_id'], name=row['name']).set(1)
            self.errors.labels(source="guilds").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="guilds").set(1)

        try:
            q_user_settings = self.exporter_db.get_user_settings_count() or []
            for row in q_user_settings:
                self.user_settings.labels(guild_id=row['_id']).set(row['total'])
            self.errors.labels(source="user_settings").set(0)
        except Exception as ex:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())
            self.errors.labels(source="user_settings").set(1)
