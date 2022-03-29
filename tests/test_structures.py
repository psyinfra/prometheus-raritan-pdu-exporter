"""Tests for prometheus_raritan_pdu_exporter/structures.py"""
from unittest.mock import patch
import time

import pytest
import vcr

from prometheus_raritan_pdu_exporter.structures import (
    PDU, Connector, Pole, Sensor, Metric)
from prometheus_raritan_pdu_exporter.globals import (
    SENSORS_NUMERIC, SENSORS_TYPES, SENSORS_UNITS)


def test_pdu(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    assert pdu.connectors == []
    assert pdu.sensors == []
    assert pdu.poles == []
    assert pdu.location == 'https://pdublue.rack0.htc.inm7.de'
    assert pdu.name == raritan_conf['name']
    assert pdu.client.endpoint == 'https://pdublue.rack0.htc.inm7.de/bulk'
    assert not pdu.client.session.verify
    assert pdu.client.session.headers['Content-Type'] == 'application/json-rpc'


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_crawl(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()
    pdu.read_sensors()
    assert len([c for c in pdu.connectors if c.type == 'inlet']) == 1
    assert len([c for c in pdu.connectors if c.type == 'outlet']) == 36
    assert len([c for c in pdu.connectors if c.type == 'device']) == 32
    assert len(pdu.connectors) == 69
    assert all(isinstance(c, Connector) for c in pdu.connectors)
    assert len(pdu.poles) == 4
    assert all(isinstance(p, Pole) for p in pdu.poles)
    assert len(pdu.sensors) == 314
    assert all(isinstance(s, Sensor) for s in pdu.sensors)


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_crawl_connectors(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()
    outlet_rid = '/tfwopaque/pdumodel.Outlet:2.1.5/outlet.0'
    assert outlet_rid in [c.rid for c in pdu.connectors]
    outlet0 = [c for c in pdu.connectors if c.rid == outlet_rid][0]
    assert outlet0.rid == outlet_rid
    assert outlet0.type == 'outlet'
    assert outlet0.get_sensors == 'getSensors'
    assert outlet0.parent == pdu
    assert outlet0.label == '1'
    assert outlet0.socket == 'IEC 60320 C19'
    assert outlet0.custom_label == outlet0.label


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_crawl_poles(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()
    assert 1 in [p.node_id for p in pdu.poles]
    pole0 = [p for p in pdu.poles if p.node_id == 1][0]
    assert pole0.type == 'pole'
    assert pole0.label == 'I1'  # associated inlet label
    assert pole0.custom_label == 'L1'  # line + 1
    assert pole0.line == 0
    assert pole0.node_id == 1
    assert pole0.inlet.rid == '/tfwopaque/pdumodel.Inlet:2.0.4/inlet.0'
    assert pole0.parent == pdu


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_crawl_sensors(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()
    sensor_rid = '/tfwopaque/sensors.NumericSensor:4.0.3/I0Voltage'
    assert sensor_rid in [s.rid for s in pdu.sensors]
    sensor0 = [s for s in pdu.sensors if s.rid == sensor_rid][0]
    assert sensor0.rid == sensor_rid
    assert sensor0.interface == 'sensors.NumericSensor:4.0.3'
    assert sensor0.parent.rid == '/tfwopaque/pdumodel.Inlet:2.0.4/inlet.0'
    assert sensor0.name == 'voltage'
    assert sensor0.metric == 'voltage'
    assert sensor0.unit == 'volt'
    assert sensor0.longname == 'raritan_sensors_voltage_in_volt'
    assert sensor0.value is None
    assert sensor0.timestamp is None


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_read_sensors(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()
    pdu.read_sensors()
    assert all(isinstance(s.value, (int, float)) for s in pdu.sensors)
    sensor_rid = '/tfwopaque/sensors.NumericSensor:4.0.3/I0Voltage'
    assert sensor_rid in [s.rid for s in pdu.sensors]
    sensor0 = [s for s in pdu.sensors if s.rid == sensor_rid][0]
    assert sensor0.value is not None
    assert sensor0.timestamp is not None

    # Test whether clearing sensors actually clears them
    pdu.clear_sensors()
    assert all([s.value is None for s in pdu.sensors])


@pytest.mark.filterwarnings('ignore::UserWarning')
@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/readings.yaml',
    filter_headers=['authorization'])
def test_pdu_fail_read_sensors(raritan_conf):
    pdu = PDU(
        location=raritan_conf['address'], name=raritan_conf['name'],
        auth=(raritan_conf['user'], raritan_conf['pass']), insecure=True)
    pdu.crawl()

    with patch(
            'prometheus_raritan_pdu_exporter.structures.PDU.send',
            side_effect=Exception('mocked error')):
        pdu.read_sensors()
        assert all([s.value is None for s in pdu.sensors])


def test_connector():
    connector = Connector(rid='unique_id/1', type_='inlet')
    assert connector.label == '1'
    connector.update(method='metadata', label='12', plugType='C19')
    connector.update(method='settings', name='foo')
    assert connector.label == '12'
    assert connector.socket == 'C19'
    assert connector.custom_label == 'foo'


def test_pole():
    connector = Connector('unique_id/1', type_='inlet')
    pole = Pole(label='foo', line=1, node_id=2, inlet=connector)

    assert pole.type == 'pole'
    assert pole.label == connector.label
    assert pole.custom_label == 'foo'
    assert pole.line == 1
    assert pole.node_id == 2
    assert pole.inlet == connector


def test_sensor():
    sensor_metric = SENSORS_TYPES[1]
    sensor_unit = SENSORS_UNITS[2]
    timestamp = time.time()
    sensor = Sensor(rid='1', interface=SENSORS_NUMERIC[0])
    sensor.update(type={'type': 1, 'unit': 2})
    sensor.set_value(12.34, timestamp)
    longname = (
        f'raritan_sensors_{Sensor.camel_to_snake(sensor_metric)}_in_'
        f'{Sensor.camel_to_snake(sensor_unit)}')

    assert sensor.metric == sensor_metric
    assert sensor.unit == sensor_unit
    assert sensor.name == sensor_metric
    assert sensor.longname == longname
    assert sensor.value == 12.34
    assert sensor.timestamp == timestamp


def test_sensor_camel_to_snake():
    test_values = {
        'FooBarBaz': 'foo_bar_baz', 'fooBarBaz': 'foo_bar_baz',
        'FOOBarBaz': 'foo_bar_baz', 'foo_bar_baz': 'foo_bar_baz',
        'foo_bar_BAZ': 'foo_bar_baz', '_foo_bar_baz': '_foo_bar_baz',
        'fooBARbaz': 'foo_ba_rbaz', 'FOOBARBAZ': 'foobarbaz',
        'Foo1Bar2Baz3': 'foo1_bar2_baz3', '123': '123', '1_2_3': '1_2_3'}

    for arg, expected in test_values.items():
        assert Sensor.camel_to_snake(arg) == expected


def test_metric():
    sensor = Sensor(rid='foo', interface=SENSORS_NUMERIC[0])
    sensor.longname = 'foo'
    sensor2 = Sensor(rid='bar', interface=SENSORS_NUMERIC[0])
    sensor2.longname = 'bar'
    metric = Metric(sensor)
    metric.add(sensor2)

    assert metric.sensors[0] == sensor
    assert metric.sensors[1] == sensor2
    assert metric.sensors[0].rid == 'foo'
    assert metric.sensors[1].rid == 'bar'
    assert metric.interface == SENSORS_NUMERIC[0]
    assert metric.name == 'foo'


def test_parent_chaining(raritan_conf):
    pdu = PDU(location=raritan_conf['address'])
    connector = Connector(rid='unique_id/1', type_='inlet', parent=pdu)
    pole = Pole(label='foo', line=1, node_id=2, inlet=connector, parent=pdu)
    sensor = Sensor(
        rid='unqiue_id/1', interface=SENSORS_NUMERIC[0], parent=connector)

    assert sensor.parent == connector
    assert sensor.parent.parent == pdu
    assert pole.parent == pdu
    assert connector.parent == pdu
