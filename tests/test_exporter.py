"""Tests for prometheus_raritan_pdu_exporter/exporter.py"""
import vcr

from prometheus_raritan_pdu_exporter import EXPORTER_PREFIX
from prometheus_raritan_pdu_exporter.exporter import RaritanExporter
from prometheus_raritan_pdu_exporter.interfaces import Metric, MetricFamily
from prometheus_client.core import Metric as PromMetric


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_raritan_exporter_init(raritan_auth):
    exporter = RaritanExporter(config=raritan_auth)

    pdu_names = [
        'pdublue.rack0', 'pdublue.rack1', 'pdublue.rack2', 'pdured.rack0',
        'pdured.rack1', 'pdured.rack2']
    pdu_addresses = [
        'https://pdublue.rack0.htc.inm7.de',
        'https://pdublue.rack1.htc.inm7.de',
        'https://pdublue.rack2.htc.inm7.de',
        'https://pdured.rack0.htc.inm7.de',
        'https://pdured.rack1.htc.inm7.de',
        'https://pdured.rack2.htc.inm7.de']

    assert len(exporter.pdus) == len(pdu_names)
    for pdu in exporter.pdus:
        assert pdu.name in pdu_names
        assert pdu.auth.url in pdu_addresses
        n_inlets = len([c for c in pdu.connectors if c.type == 'inlet'])
        n_outlets = len([c for c in pdu.connectors if c.type == 'outlet'])
        n_devices = len([c for c in pdu.connectors if c.type == 'device'])
        assert n_inlets == pdu.n_inlets == 1
        assert n_outlets == pdu.n_outlets == 36
        assert n_devices == pdu.n_devices == 64
        assert len(pdu.connectors) == 101
        assert len(pdu.poles) == pdu.n_poles == 4

        # pdu.sensors only contains _used_ sensors
        # number of used sensors is variable depending on PDU setup
        assert len(pdu.sensors) == pdu.n_sensors > 0


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_raritan_exporter_read(raritan_auth):
    exporter = RaritanExporter(config=raritan_auth)
    readings = exporter.read()

    # readings depend on _used_ sensors, which is variable
    assert len(readings) > 0
    assert sum([len(reading.metrics) for reading in readings]) > 0

    for family in readings:
        assert isinstance(family, MetricFamily)
        assert family.interface
        assert family.name
        assert family.description

        for metric in family.metrics:
            assert isinstance(metric, Metric)
            assert metric.pdu
            assert metric.label
            assert metric.type
            assert metric.connector_id

            if metric.is_numeric:
                assert isinstance(metric.value, (float, int))


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_raritan_exporter_collect(raritan_auth):
    exporter = RaritanExporter(config=raritan_auth)
    results = exporter.collect()
    pdu_names = [
        'pdublue.rack0', 'pdublue.rack1', 'pdublue.rack2', 'pdured.rack0',
        'pdured.rack1', 'pdured.rack2']

    for metric in results:
        assert isinstance(metric, PromMetric)
        assert metric.name.startswith(f'{EXPORTER_PREFIX}_')

        for sample in metric.samples:
            assert sample.labels['pdu'] in pdu_names
            assert isinstance(sample.value, (int, float))
