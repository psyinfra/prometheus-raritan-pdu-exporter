from typing import Optional, List
import argparse
import urllib3
import logging
import time

from prometheus_client import (start_http_server, REGISTRY, Summary)
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily

from raritan.structures import PDU, Metric
from raritan.globals import RARITAN_GAUGES, RARITAN_COUNTERS


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
        '-a', '--address',
        metavar='address',
        required=True,
        help='address of the raritan PDU server'
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
        '--user',
        metavar='user',
        required=False,
        help='raritan API user',
        default=None
    )
    parser.add_argument(
        '--password',
        metavar='password',
        required=False,
        help='raritan API password',
        default=None
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
        REGISTRY.register(RaritanExporter(
            args.address, (args.user, args.password), args.insecure)
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


class RaritanExporter:
    """Prometheus exporter for Raritan PDUs

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
    """
    def __init__(self, instance: str, 
                 auth: Optional[tuple] = (), insecure: Optional[bool] = False):
        self.pdu = PDU(instance, auth=auth, insecure=insecure)
        self.pdu.get_sources()

    def get_reading(self) -> List[Metric]:
        """Obtain a sensor reading for all sensors from all PDUs"""
        self.pdu.read_sensors()

        # convert all PDU.Sensors to Metric format
        metrics = []
        for sensor in self.pdu.sensors:
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

