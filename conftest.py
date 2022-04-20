from dataclasses import dataclass, field
from typing import Optional
import json
import os

import pytest


@dataclass
class RaritanConfig:
    file: str
    name: str
    url: str
    user: str
    password: str
    ssl: Optional[bool] = field(default=False)


@pytest.fixture(scope='module')
def raritan_conf():
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """

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
