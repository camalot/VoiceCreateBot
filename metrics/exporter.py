from prometheus_client import start_http_server, Gauge, Enum
from .voicecreate import VoiceCreateMetrics
from .config import VoiceCreateMetricsConfig
class MetricsExporter():

    def run(self):
        config = VoiceCreateMetricsConfig("metrics/config.yml")
        app_metrics = VoiceCreateMetrics(config)
        start_http_server(config.metrics["port"])
        app_metrics.run_metrics_loop()

