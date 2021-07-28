#!/usr/bin/env python
import argparse
import urllib3
import logging
import time
import urllib.parse

from prometheus_client import start_http_server, REGISTRY
from raritan.exporter import RaritanExporter

DEFAULT_PORT = 9840

# Raritan PDU has no SSL certificate, ignore the ensuing warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# External (root level) logging level
logging.basicConfig(
    level=logging.WARNING, format='[%(asctime)s] %(levelname)s: %(message)s')

# Internal logging level
logger = logging.getLogger('prometheus_raritan_pdu_exporter')
logger.setLevel(level=logging.DEBUG)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Python-based Raritan PDU exporter for prometheus.io')
    parser.add_argument(
        '-c', '--config', metavar='config', required=True,
        help='configuration json file containing PDU addresses and login info')
    parser.add_argument(
        '-w', '--web.listen-address', metavar='listen_address', required=False,
        type=str, help='Address and port to listen on',
        default=f':{DEFAULT_PORT}')
    parser.add_argument(
        '-t', '--threading', dest='threading', required=False, default=False,
        action='store_true',
        help='whether to use multi-threading for sensor readings (faster)')
    parser.add_argument(
        '-k', '--insecure', dest='insecure', required=False, default=False,
        action='store_true',
        help='allow a connection to an insecure raritan API')
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        listen_address = urllib.parse.urlsplit(f'//{args.listen_address}')
        addr = listen_address.hostname if listen_address.hostname else ''
        port = listen_address.port if listen_address.port else DEFAULT_PORT

        REGISTRY.register(RaritanExporter(
            config=args.config, threading=args.threading,
            insecure=args.insecure))
        logger.info('listening on :%s' % listen_address.netloc)
        start_http_server(port, addr=addr)

        while True:
            time.sleep(1)

    except BrokenPipeError as exc:
        logger.error(exc)

    except KeyboardInterrupt:
        logger.info('interrupted by user')
        exit(0)


if __name__ == '__main__':
    main()
