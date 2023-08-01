import inspect
import os
import time
from prometheus_client import Gauge
from .lib.mongodb.exporter import ExporterMongoDatabase

class VoiceCreateMetrics:
    def __init__(self, config):
        self._method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]

        self.namespace = "voicecreate"
        self.polling_interval_seconds = config.metrics["pollingInterval"]
        self.config = config

        self.db = ExporterMongoDatabase()

        self.guilds = Gauge(
            namespace=self.namespace,
            name=f"guild",
            documentation="The guilds that the bot is in",
            labelnames=["guild_id", "name"])


    def run_metrics_loop(self):
        """Metrics fetching loop"""
        while True:
            print(f"begin metrics fetch")
            self.fetch()
            print(f"end metrics fetch")
            time.sleep(self.polling_interval_seconds)

    def fetch(self):
        q_guilds = self.db.get_guilds()
        known_guilds = []
        for row in q_guilds:
            known_guilds.append(row['guild_id'])
            self.guilds.labels(guild_id=row['guild_id'], name=row['name']).set(1)
