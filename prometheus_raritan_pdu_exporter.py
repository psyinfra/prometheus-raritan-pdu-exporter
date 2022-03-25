#!/usr/bin/env python3
from prometheus_raritan_pdu_exporter import LogLevels

import argparse
import urllib3
import logging
import time
import urllib.parse

from prometheus_client import start_http_server, REGISTRY
from prometheus_raritan_pdu_exporter.exporter import RaritanExporter

DEFAULT_PORT = 9840

# Raritan PDU has no SSL certificate, ignore the ensuing warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# External (root level) logging level
logging.basicConfig(
    level=logging.WARNING, format='[%(asctime)s] %(levelname)s: %(message)s')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Python-based Raritan PDU exporter for prometheus.io')
    parser.add_argument(
        '-c', '--config', metavar='config', required=True,
        help='configuration json file containing PDU addresses and login info')
    parser.add_argument(
        '-w', '--web.listen-address', dest='listen_address', required=False,
        type=str, help='Address and port to listen on (default = :9840)',
        default=f':{DEFAULT_PORT}')
    parser.add_argument(
        '-k', '--insecure', dest='insecure', required=False, default=False,
        action='store_true',
        help='allow a connection to an insecure Raritan API')
    parser.add_argument(
        '-l', '--log-level', dest='log_level', required=False, type=str,
        help='Logging level (default = warning)', default='warning')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.log_level in LogLevels.all:
        logger = logging.getLogger('prometheus_raritan_pdu_exporter')
        logger.setLevel(level=LogLevels.all[args.log_level])
        logger.debug(f'Current log level: {logger.level}')
    else:
        raise ValueError(
            f'Unknown log-level: {args.log_level}. '
            f'Try {*LogLevels.all.keys(),}')

    listen_address = urllib.parse.urlsplit(f'//{args.listen_address}')
    addr = listen_address.hostname if listen_address.hostname else ''
    port = listen_address.port if listen_address.port else DEFAULT_PORT

    try:
        REGISTRY.register(RaritanExporter(
            config=args.config, insecure=args.insecure))
        logger.info('listening on %s' % listen_address.netloc)
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
