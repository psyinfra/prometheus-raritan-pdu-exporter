from typing import Optional, List, Union
from threading import Thread
import json

from prometheus_client import Summary
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily

from .structures import PDU, Metric
from .globals import RARITAN_GAUGES, RARITAN_COUNTERS


# Measure collection time
REQUEST_TIME = Summary('raritan_collector_collect_seconds',
                       'Time spent to collect metrics from the Raritan PDU')


class RaritanExporter:
    """Prometheus exporter for Raritan PDUs.

    Collects metrics from multiple PDUs at the same time. If threading is
    enabled, multiple threads will be used to collect sensor readings which is
    considerably faster.

    Parameters
    ----------
    config : str
        Path to the configuration file, containing PDU location, username,
        and password combinations for all PDUs to be monitored
    threading : bool, optional
        Whether to use multithreading or serial processing. Note that serial
        processing becomes slower when more PDUs are added. Since the HTTP
        request to the json-rpc API and waiting for its response takes longest,
        threading is recommended when more than 1 PDU is being monitored
    insecure : bool, optional
        Whether to allow a connection to an insecure Raritan API
    """
    def __init__(
            self, config: Union[str, dict], insecure: Optional[bool] = True):
        self.threading = False

        if isinstance(config, str):
            config = self.load_config(config)

        self.pdus = self.get_pdus(config, insecure)

    @staticmethod
    def load_config(config: str) -> dict:
        with open(config) as json_file:
            data = json.load(json_file)
        return data

    def get_pdus(self, config: dict, insecure: Optional[bool] = True) -> list:
        """Set up all PDUs found in the configuration file"""
        pdus = [
            PDU(v['address'], k, (v['user'], v['password']), insecure)
            for k, v in config.items()]
        self.threading = True if len(pdus) > 1 else False

        if self.threading:
            threads = []

            for pdu in pdus:
                threads.append(Thread(target=pdu.crawl))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for pdu in pdus:
                pdu.crawl()

        return pdus

    def get_reading(self) -> List[Metric]:
        """Obtain a sensor reading for all sensors from all PDUs"""
        if self.threading:
            threads = []
            for pdu in self.pdus:
                threads.append(Thread(target=pdu.read_sensors))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for pdu in self.pdus:
                pdu.read_sensors()

        # convert all PDU.Sensors to Metric format
        metrics = []
        for pdu in self.pdus:
            for sensor in pdu.sensors:
                name = sensor.longname
                keys = [m.name for m in metrics]
                metric_id = keys.index(name) if name in keys else None

                if metric_id is not None:
                    metrics[metric_id].add(sensor)
                else:
                    metrics.append(Metric(sensor))

        return metrics

    @REQUEST_TIME.time()
    def collect(self):
        """Collect sensor readings, called every time the http server
        containing the Raritan PDU metrics is requested"""
        metrics = self.get_reading()
        labels = ['pdu', 'label', 'type', 'connector_id']

        # Expose all metrics
        for metric in metrics:
            if metric.interface in RARITAN_GAUGES:
                g = GaugeMetricFamily(
                    metric.name, metric.description, labels=labels)

                for sensor in metric.sensors:
                    if PDU.is_null(sensor):
                        continue

                    g.add_metric([
                        sensor.parent.parent.location,
                        sensor.parent.custom_label, sensor.parent.type,
                        sensor.parent.label], sensor.value)

            elif metric.interface in RARITAN_COUNTERS:
                g = CounterMetricFamily(
                    metric.name, metric.description, labels=labels)

                for sensor in metric.sensors:
                    if PDU.is_null(sensor):
                        continue

                    g.add_metric([
                        sensor.parent.parent.location,
                        sensor.parent.custom_label, sensor.parent.type,
                        sensor.parent.label], sensor.value)

            else:  # interface cannot be collected (i.e., state sensors)
                continue

            yield g
