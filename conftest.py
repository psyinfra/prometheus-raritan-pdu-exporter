from dataclasses import dataclass, field
from typing import Optional
import json
import os

import pytest
import vcr

from prometheus_raritan_pdu_exporter.exporter import RaritanExporter


@dataclass
class RaritanConfig:
    file: str
    name: str
    url: str
    user: str = field(repr=False)
    password: str = field(repr=False)
    ssl: Optional[bool] = field(default=False)


def config():
    raritan_config_file = (
        'tests/fixtures/config.json'
        if os.path.exists('tests/fixtures/config.json')
        else 'tests/fixtures/config.json-example')

    with open(raritan_config_file) as json_file:
        config = json.load(json_file)

    key = list(config.keys())[0]
    return RaritanConfig(
        file=raritan_config_file, name=key, url=config[key]['url'],
        user=config[key]['user'], password=config[key]['password'],
        ssl=config[key]['ssl'])


@pytest.fixture(scope='module')
def raritan_conf():
    return config()


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def pytest_sessionstart(session):
    """Collect data sample from configured PDUs and store it as a cassette"""
    raritan_conf = config()
    exporter = RaritanExporter(config=raritan_conf.file)
    _ = exporter.read()
