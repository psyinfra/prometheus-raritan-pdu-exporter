"""Tests for prometheus_raritan_pdu_exporter/exporter.py"""
import vcr

from prometheus_raritan_pdu_exporter.exporter import RaritanExporter
from prometheus_client.core import Metric


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/exporter.yaml',
    filter_headers=['authorization'])
def test_raritan_exporter_single(raritan_conf):
    exporter = RaritanExporter(
        config=raritan_conf['config_file'], insecure=True)

    # PDUs being tested
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

    # fixtures/config.json and dummy credentials have more than 1 PDU
    assert exporter.threading

    for pdu in exporter.pdus:
        assert pdu.name in pdu_names

    results = exporter.collect()

    for metric in results:
        assert isinstance(metric, Metric)
        assert metric.name.startswith('raritan_sensors_')

        for sample in metric.samples:
            assert sample.labels['pdu'] in pdu_addresses
            assert isinstance(sample.value, (int, float))
