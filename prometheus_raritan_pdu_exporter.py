#!/usr/bin/env python3
import argparse
import logging
import time
import urllib.parse

from prometheus_client import start_http_server, REGISTRY

from prometheus_raritan_pdu_exporter import DEFAULT_PORT
from prometheus_raritan_pdu_exporter.exporter import RaritanExporter


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
        '-s', '--ssl', dest='ssl', required=False, default=False,
        action='store_true',
        help='Only allow a connection to a secure Raritan API')
    parser.add_argument(
        '-l', '--log-level', dest='log_level', required=False, type=str,
        help='Logging level (default = WARNING)', default='WARNING')
    return parser.parse_args()


def main():
    args = parse_args()
    level_names = [
        logging.getLevelName(i) for i in range(1, 101)
        if not logging.getLevelName(i).startswith('Level')]
    log_level = args.log_level.upper()

    if log_level in level_names:
        logger = logging.getLogger('prometheus_raritan_pdu_exporter')
        logger.setLevel(level=log_level)
        logger.info(
            f'Current log level: {logging.getLevelName(logger.level)}')
    else:
        raise ValueError(
            f'Unknown log-level: \'{log_level}\' try using {*level_names,}')

    listen_address = urllib.parse.urlsplit(f'//{args.listen_address}')
    addr = listen_address.hostname if listen_address.hostname else '0.0.0.0'
    port = listen_address.port if listen_address.port else DEFAULT_PORT

    REGISTRY.register(RaritanExporter(config=args.config))
    start_http_server(port, addr=addr)
    logger.info('listening on %s' % listen_address.netloc)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
        exit(0)


if __name__ == '__main__':
    main()
