import json
import os

import pytest
import vcr

from prometheus_raritan_pdu_exporter.exporter import RaritanExporter
from prometheus_raritan_pdu_exporter.jsonrpc import RaritanAuth


def config():
    raritan_config_file = (
        'tests/fixtures/config.json'
        if os.path.exists('tests/fixtures/config.json')
        else 'tests/fixtures/config.json-example')

    with open(raritan_config_file) as json_file:
        config = json.load(json_file)

    return [RaritanAuth(
        name=k, url=v['url'], user=v['user'], password=v['password'],
        verify_ssl=v['verify_ssl']) for k, v in config.items()]


@pytest.fixture(scope='module')
def raritan_auth():
    return config()


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def pytest_sessionstart(session):
    """Collect data sample from configured PDUs and store it as a cassette"""
    auth = config()
    exporter = RaritanExporter(config=auth)
    _ = exporter.read()
