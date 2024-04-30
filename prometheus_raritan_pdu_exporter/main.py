from typing import List
import argparse
import json
import logging
import time
import urllib.parse
from wsgiref.simple_server import make_server

from prometheus_client import MetricsHandler, make_wsgi_app, REGISTRY

from . import DEFAULT_PORT
from .exporter import RaritanExporter
from .jsonrpc import RaritanAuth


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


def set_log_level(log_level: list) -> logging.Logger:
    level_names = [
        logging.getLevelName(i) for i in range(1, 101)
        if not logging.getLevelName(i).startswith('Level')]
    log_level = [log.upper() for log in log_level]

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

    return logger


def read_config(config: str) -> List[RaritanAuth]:
    with open(config) as json_file:
        data = json.load(json_file)

    config_data = []
    for k, v in data.items():
        try:
            url = v['url']
            user = v['user']
            password = v['password']
            verify_ssl = v['verify_ssl']
            name = k
        except KeyError as exc:
            raise KeyError(
                f'Error in configuration file: {exc} not found for {k}')

        config_data.append(RaritanAuth(
            name=name, url=url, user=user, password=password,
            verify_ssl=verify_ssl))

    return config_data


class HealthcheckHandler(MetricsHandler):
    def do_GET(self):
        logging.debug(self.path)
        if self.path == '/healthcheck':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'Server is running')
        else:
            super().do_GET()


def main():
    args = parse_args()

    # Set up logging
    logger = set_log_level(args.log_level)
    internal_log_level = logging.getLevelName(logger.level)
    external_log_level = logging.getLevelName(logging.root.level)
    logger.info(f'Internal log level: {internal_log_level}')
    logger.info(f'External log level: {external_log_level}')

    try:
        # Read config
        logger.info(f'Loading configuration file \'{args.config}\'')
        config = read_config(args.config)

        # Set up http server
        listen_addr = urllib.parse.urlsplit(f'//{args.listen_address}')
        addr = listen_addr.hostname if listen_addr.hostname else '0.0.0.0'
        port = listen_addr.port if listen_addr.port else DEFAULT_PORT
        logger.info('listening on %s' % listen_addr.netloc)
        REGISTRY.register(RaritanExporter(config=config))
        prometheus_application = make_wsgi_app()
        httpd = make_server(
            addr,
            port,
            prometheus_application,
            handler_class=HealthcheckHandler
        )
        httpd.serve_forever()
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
