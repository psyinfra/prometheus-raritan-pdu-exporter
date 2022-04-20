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
        type=str,
        help=f'Address and port to listen on (default = :{DEFAULT_PORT})',
        default=f':{DEFAULT_PORT}')
    parser.add_argument(
        '-l', '--log', dest='log_level', nargs='+', required=False,
        type=str, default=['WARNING', 'CRITICAL'],
        help='Specify logging level for internal and external logging, '
             'respectively (Default is WARNING,CRITICAL)')
    return parser.parse_args()


def main():
    args = parse_args()
    level_names = [
        logging.getLevelName(i) for i in range(1, 101)
        if not logging.getLevelName(i).startswith('Level')]
    log_level = [log.upper() for log in args.log_level]

    if len(log_level) == 1:
        log_level = log_level[0].split(',')  # adjust for , list separation

    if len(log_level) == 1:
        log_level.append('CRITICAL')
    elif len(log_level) > 2:
        raise SystemExit(
            f'{len(log_level)} log levels given, but 2 is the maximum')

    internal_log_level, external_log_level = log_level
    if external_log_level in level_names:
        logging.basicConfig(
            level=external_log_level,
            format='[%(asctime)s] %(levelname)s: %(message)s')
    else:
        raise SystemExit(
            f'Unknown log-level: \'{external_log_level}\' try using '
            f'{*level_names,}')

    if internal_log_level in level_names:
        logger = logging.getLogger('prometheus_raritan_pdu_exporter')
        logger.setLevel(level=internal_log_level)
    else:
        raise SystemExit(
            f'Unknown log-level: \'{internal_log_level}\' try using '
            f'{*level_names,}')

    logger.info(f'Internal log level: {logging.getLevelName(logger.level)}')
    logger.info(
        f'External log level: {logging.getLevelName(logging.root.level)}')

    listen_address = urllib.parse.urlsplit(f'//{args.listen_address}')
    addr = listen_address.hostname if listen_address.hostname else '0.0.0.0'
    port = listen_address.port if listen_address.port else DEFAULT_PORT

    try:
        REGISTRY.register(RaritanExporter(config=args.config))
        start_http_server(port, addr=addr)
        logger.info('listening on %s' % listen_address.netloc)
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
        exit(0)
    except Exception as exc:
        logger.error(exc)
        logger.critical(
            'Exporter shut down due to an error during the setup procedure. '
            'Please contact your administrator.')
        exit(1)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
        exit(0)
    except Exception as exc:
        logger.error(exc)
        logger.critical(
            'Exporter shut down unexpectedly. Please contact your '
            'administrator.')
        exit(1)


if __name__ == '__main__':
    main()
