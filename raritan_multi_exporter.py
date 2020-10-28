from raritan.structures import PDU, Metric
from raritan.globals import RARITAN_GAUGES, RARITAN_COUNTERS
from prometheus_client import (start_http_server, REGISTRY,
                               Summary)
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from typing import Optional, List
from threading import Thread
import argparse
import urllib3
import logging
import time
import json

# Raritan PDU has no SSL certificate, ignore the ensuing warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# External (root level) logging level
logging.basicConfig(
    level=logging.WARNING,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)

# Internal logging level
logger = logging.getLogger('raritan_exporter')
logger.setLevel(level=logging.DEBUG)

# Measure collection time
REQUEST_TIME = Summary('raritan_collector_collect_seconds',
                       'Time spent to collect metrics from the Raritan PDU')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Python-based Raritan PDU exporter for prometheus.io'
    )
    parser.add_argument(
        '-c', '--config',
        metavar='config',
        required=True,
        help='configuration json file containing PDU addresses and login info'
    )
    parser.add_argument(
        '-p', '--port',
        metavar='port',
        required=False,
        type=int,
        help='listen to this port',
        default=8001
    )
    parser.add_argument(
        '-t', '--threading',
        dest='threading',
        required=False,
        action='store_true',
        help='whether to use multi-threading for sensor readings (faster)',
        default=False
    )
    parser.add_argument(
        '-k', '--insecure',
        dest='insecure',
        required=False,
        action='store_true',
        help='allow a connection to an insecure raritan API',
        default=False
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        port = int(args.port)
        REGISTRY.register(
            MultiRaritanExporter(args.config, args.threading, args.insecure)
        )
        logger.info('listening on :%s' % port)
        start_http_server(port)

        while True:
            time.sleep(1)

    except BrokenPipeError as exc:
        logger.error(exc)

    except KeyboardInterrupt:
        logger.info('interrupted by user')
        exit(0)


class MultiRaritanExporter:
    """Prometheus exporter for multiple Raritan PDUs.

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
        Whether to allow a connection to an insecure raritan API
    """
    def __init__(self, config: str,
                 threading: Optional[bool] = True,
                 insecure: Optional[bool] = True):
        self.threading = threading
        self.pdus = self.get_pdus(config, insecure)

    def get_pdus(self, config: str, insecure: Optional[bool] = True) -> list:
        """Set up all PDUs found in the configuration file"""
        with open(config) as json_file:
            data = json.load(json_file)

        pdus = [PDU(v['address'], k, (v['user'], v['password']), insecure)
                for k, v in data.items()]

        if self.threading:
            threads = []

            for pdu in pdus:
                threads.append(Thread(target=pdu.get_sources))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for pdu in pdus:
                pdu.get_sources()

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
        labels = ['pdu', 'label', 'type']

        # Expose all metrics
        for metric in metrics:
            if metric.interface in RARITAN_GAUGES:
                g = GaugeMetricFamily(
                    metric.name, 
                    metric.description, 
                    labels=labels
                )
                for sensor in metric.sensors:
                    if sensor.value is None:
                        continue

                    if sensor.parent.custom_label:
                        label = sensor.parent.custom_label
                    else:
                        label = sensor.parent.label

                    g.add_metric(
                        [sensor.parent.parent.location, 
                         label,
                         sensor.parent.type],
                        sensor.value
                    )

            elif metric.interface in RARITAN_COUNTERS:
                g = CounterMetricFamily(
                    metric.name, 
                    metric.description, 
                    labels=labels
                )
                for sensor in metric.sensors:
                    if sensor.value is None:
                        continue

                    if sensor.parent.custom_label:
                        label = sensor.parent.custom_label
                    else:
                        label = sensor.parent.label

                    g.add_metric(
                        [sensor.parent.parent.location, 
                         label,
                         sensor.parent.type],
                        sensor.value
                    )

            else:  # interface cannot be collected (i.e., state sensors)
                continue

            yield g


if __name__ == '__main__':
    main()

