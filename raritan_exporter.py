from typing import Optional, List
import argparse
import urllib3
import logging
import time

from prometheus_client import (start_http_server, REGISTRY, Summary)
from raritan.exporter import RaritanExporter

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
            address=args.address,
            auth=(args.user, args.password),
            insecure=args.insecure
        ))
        logger.info('listening on :%s' % port)
        start_http_server(port)

        while True:
            time.sleep(1)

    except BrokenPipeError as exc:
        logger.error(exc)

    except KeyboardInterrupt:
        logger.info('interrupted by user')
        exit(0)


if __name__ == '__main__':
    main()

