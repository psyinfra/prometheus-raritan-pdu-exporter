"""Test behavior for expected failure states"""
import pytest
import asyncio
import vcr

from prometheus_raritan_pdu_exporter.interfaces import PDU
from prometheus_raritan_pdu_exporter.jsonrpc import Request, EmptyResponse


@pytest.fixture
def test_exception():
    class TestException(Exception):
        def __init__(self):
            super().__init__()
    return TestException


def test_empty_response_connector_rids(
        raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned during any of the setup steps"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    monkeypatch.setattr(Request, 'send', mock_send)

    with pytest.raises(test_exception):
        _ = asyncio.run(pdu._connector_rids())


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_empty_response_connector_metadata(
        raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned during any of the setup steps"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    connectors = asyncio.run(pdu._connector_rids())
    monkeypatch.setattr(Request, 'send', mock_send)

    with pytest.raises(test_exception):
        _ = asyncio.run(pdu._connector_metadata(connectors))


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_empty_response_connector_settings(
        raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned during any of the setup steps"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    connectors = asyncio.run(pdu._connector_rids())
    connectors = asyncio.run(pdu._connector_metadata(connectors))
    monkeypatch.setattr(Request, 'send', mock_send)

    with pytest.raises(test_exception):
        _ = asyncio.run(pdu._connector_settings(connectors))


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_empty_response_sensors_from_poles(
        raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned during any of the setup steps"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    monkeypatch.setattr(Request, 'send', mock_send)

    with pytest.raises(test_exception):
        _ = asyncio.run(pdu._sensors_from_poles())


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_empty_response_sensors_from_connectors(
        raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned during any of the setup steps"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu._connectors())

    monkeypatch.setattr(Request, 'send', mock_send)

    with pytest.raises(test_exception):
        _ = asyncio.run(pdu._sensors_from_connectors(pdu.connectors))


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_empty_response_read(raritan_conf, test_exception, monkeypatch):
    """EmptyResponse returned when reading from sensors"""
    async def mock_send(self):
        response = EmptyResponse(exception=test_exception())
        return response

    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    monkeypatch.setattr(Request, 'send', mock_send)

    metrics = asyncio.run(pdu.read())
    assert len(metrics) == 0
