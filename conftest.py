import os
import json

import pytest


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

    pdu_name = list(config.keys())[0]
    pdu_address = config[pdu_name]['address']
    pdu_user = config[pdu_name]['user']
    pdu_password = config[pdu_name]['password']

    return {
        'config_file': raritan_config_file, 'name': pdu_name,
        'address': pdu_address, 'user': pdu_user, 'pass': pdu_password}
