"""Tests for prometheus_raritan_pdu_exporter/interfaces.py"""
from unittest.mock import patch
import time

import asyncio
import pytest
import vcr

from prometheus_raritan_pdu_exporter.interfaces import (
    InterfaceError, MetricMismatchError, PDU, Connector, Pole, Sensor, Metric,
    MetricFamily)
from prometheus_raritan_pdu_exporter.jsonrpc import RaritanAuth
from prometheus_raritan_pdu_exporter import (
    EXPORTER_PREFIX, SENSORS_TYPES, SENSORS_COUNTERS, SENSORS_GAUGES,
    SENSORS_UNITS, SENSORS_DESCRIPTION)


def test_pdu_post_init(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    assert pdu.connectors == []
    assert pdu.poles == []
    assert pdu.sensors == []
    assert pdu.name == raritan_conf.name
    assert isinstance(pdu.auth, RaritanAuth)
    assert pdu.auth.url == 'https://pdublue.rack0.htc.inm7.de'
    assert pdu.auth.user == raritan_conf.user
    assert pdu.auth.password == raritan_conf.password
    assert pdu.auth.ssl == raritan_conf.ssl


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_setup(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    n_inlets = len([c for c in pdu.connectors if c.type == 'inlet'])
    n_outlets = len([c for c in pdu.connectors if c.type == 'outlet'])
    n_devices = len([c for c in pdu.connectors if c.type == 'device'])

    assert n_inlets == pdu.n_inlets == 1
    assert n_outlets == pdu.n_outlets == 36
    assert n_devices == pdu.n_devices == 32
    assert len(pdu.connectors) == 69
    assert len(pdu.poles) == pdu.n_poles == 4
    assert len(pdu.sensors) == pdu.n_sensors > 0

    assert all(isinstance(c, Connector) for c in pdu.connectors)
    assert all(isinstance(p, Pole) for p in pdu.poles)
    assert all(isinstance(s, Sensor) for s in pdu.sensors)


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_setup_connectors(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    outlet_rid = '/tfwopaque/pdumodel.Outlet:2.1.5/outlet.0'
    assert outlet_rid in [c.rid for c in pdu.connectors]
    outlet = [c for c in pdu.connectors if c.rid == outlet_rid][0]

    assert outlet.pdu == pdu
    assert outlet.rid == outlet_rid
    assert outlet.id == '1'
    assert outlet.name == '1'  # TODO: may be different, custom-labeled
    assert outlet.type == 'outlet'


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_setup_poles(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    assert 1 in [p.id for p in pdu.poles]
    pole = [p for p in pdu.poles if p.id == 1][0]
    assert pole.pdu == pdu
    assert pole.id == 1
    assert pole.name == 'L1'


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_setup_sensors(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    sensor_rid = '/tfwopaque/sensors.NumericSensor:4.0.3/I0Voltage'
    assert sensor_rid in [s.rid for s in pdu.sensors]
    sensor = [s for s in pdu.sensors if s.rid == sensor_rid][0]

    assert sensor.rid == sensor_rid
    assert sensor.interface == 'gauge'  # sensors.NumericSensor:4.0.3
    assert sensor.name == f'{EXPORTER_PREFIX}_voltage_volt'
    assert sensor.parent.rid == '/tfwopaque/pdumodel.Inlet:2.0.4/inlet.0'


@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_read(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())
    metrics = asyncio.run(pdu.read())

    assert all(isinstance(m, Metric) for m in metrics)
    sensor_rid = '/tfwopaque/sensors.NumericSensor:4.0.3/I0Voltage'
    assert sensor_rid in [m.sensor_rid for m in metrics]
    metric = [m for m in metrics if m.sensor_rid == sensor_rid][0]
    assert metric.value is not None
    assert metric.timestamp is not None


@pytest.mark.filterwarnings('ignore::UserWarning')
@vcr.use_cassette(
    'tests/fixtures/vcr_cassettes/data.yaml',
    filter_headers=['authorization'])
def test_pdu_read_fail(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    asyncio.run(pdu.setup())

    with patch(
            'prometheus_raritan_pdu_exporter.jsonrpc.Request.send',
            side_effect=Exception('mocked error')):
        metrics = asyncio.run(pdu.read())
        assert not metrics


def test_connector(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    connector = Connector(pdu=pdu, rid='unique_id/1', type='inlet')
    assert connector.pdu == pdu
    assert connector.rid == 'unique_id/1'
    assert connector.type == 'inlet'
    assert connector.id == '1'
    assert connector.name == '1'
    assert connector.__dataclass_params__.frozen


def test_pole(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)

    pole = Pole(pdu=pdu, id=1)
    assert pole.pdu == pdu
    assert pole.id == 1
    assert pole.name == 'L1'
    assert pole.type == 'pole'
    assert pole.__dataclass_params__.frozen


def test_sensor(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    connector = Connector(pdu=pdu, rid='unique_id/1', type='inlet')

    sensor = Sensor(
        rid='1', interface=SENSORS_GAUGES[0], metric=1, unit=2,
        parent=connector)

    assert sensor.rid == '1'
    assert sensor.interface == 'gauge'
    assert sensor.name == \
           f'{EXPORTER_PREFIX}_{SENSORS_TYPES[1]}_{SENSORS_UNITS[2]}'
    assert sensor.__dataclass_params__.frozen

    sensor = Sensor(
        rid='1', interface=SENSORS_COUNTERS[0], metric=1, unit=0,
        parent=connector)
    assert sensor.interface == 'counter'
    assert sensor.name == f'{EXPORTER_PREFIX}_{SENSORS_TYPES[1]}_total'

    with pytest.raises(InterfaceError):
        Sensor(rid='1', interface='foo', metric=1, unit=2, parent=connector)


def test_sensor_camel_to_snake():
    test_values = {
        'FooBarBaz': 'foo_bar_baz', 'fooBarBaz': 'foo_bar_baz',
        'FOOBarBaz': 'foo_bar_baz', 'foo_bar_baz': 'foo_bar_baz',
        'foo_bar_BAZ': 'foo_bar_baz', '_foo_bar_baz': '_foo_bar_baz',
        'fooBARbaz': 'foo_ba_rbaz', 'FOOBARBAZ': 'foobarbaz',
        'Foo1Bar2Baz3': 'foo1_bar2_baz3', '123': '123', '1_2_3': '1_2_3'}

    for arg, expected in test_values.items():
        assert Sensor.camel_to_snake(arg) == expected


def test_metric(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    connector = Connector(pdu=pdu, rid='unique_id/1', type='inlet')
    sensor = Sensor(
        rid='1', interface=SENSORS_GAUGES[0], metric=1, unit=2,
        parent=connector)

    metric = Metric(sensor=sensor, value=12.34, timestamp=time.time())

    assert metric.name == sensor.name
    assert metric.interface == sensor.interface
    assert metric.pdu == sensor.parent.pdu.name
    assert metric.label == sensor.parent.name
    assert metric.type == sensor.parent.type
    assert metric.connector_id == sensor.parent.id
    assert metric.sensor_rid == sensor.rid
    assert metric.is_numeric
    metric.value = None
    assert not metric.is_numeric
    metric.value = 'none'
    assert not metric.is_numeric


def test_metric_family(raritan_conf):
    pdu = PDU(
        url=raritan_conf.url, user=raritan_conf.user,
        password=raritan_conf.password, ssl=raritan_conf.ssl,
        name=raritan_conf.name)
    connector = Connector(pdu=pdu, rid='unique_id/1', type='inlet')
    sensor = Sensor(
        rid='1', interface=SENSORS_GAUGES[0], metric=1, unit=1,
        parent=connector)
    metric = Metric(sensor=sensor, value=12.34, timestamp=time.time())

    family = MetricFamily(metric=metric)

    assert family.name == metric.name
    assert family.interface == metric.interface
    assert family.description == SENSORS_DESCRIPTION[
        f'{EXPORTER_PREFIX}_voltage_volt']
    assert len(family.metrics) == 1
    assert family.metrics[0] is metric

    metric2 = Metric(sensor=sensor, value=56.78, timestamp=time.time())
    family.add(metric2)
    assert len(family.metrics) == 2
    assert family.metrics[1] is metric2

    sensor2 = Sensor(
        rid='2', interface=SENSORS_GAUGES[0], metric=2, unit=2,
        parent=connector)
    metric3 = Metric(sensor=sensor2, value=90.12, timestamp=time.time())

    with pytest.raises(MetricMismatchError):
        family.add(metric3)
