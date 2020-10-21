import time

from pytest import fixture, raises as praises

from raritan import structures as struct
from raritan.globals import SENSORS_NUMERIC, SENSORS_TYPES, SENSORS_UNITS


def test_camel_to_snake():
    assert struct.camel_to_snake('fooBarBaz') == 'foo_bar_baz'
    assert struct.camel_to_snake('foobarbaz') == 'foobarbaz'
    assert struct.camel_to_snake('foo_barBaz') == 'foo_bar_baz'
    assert struct.camel_to_snake('Foobarbaz') == 'foobarbaz'


def test_pdu_object():
    location = 'http://127.0.0.1:30000'
    pdu = struct.PDU(location, insecure=True)

    assert pdu.location == '127.0.0.1:30000'
    assert pdu.client.endpoint == f'{location}/bulk'
    assert not pdu.client.verify

    # TODO: Make a get_sources and read_sensors test.
    #   These tests require a connection to a raritan PDU


def test_connector_object():
    uid = 'unique_id/1'
    type_ = 'inlet'
    custom_label = 'foo'
    connector = struct.Connector(uid, type_=type_)
    assert connector.label == 'unique_id'
    connector.update(
        method='metadata',
        label='12',
        plugType='C19',
    )
    connector.update(method='settings', custom_label=custom_label)
    assert connector.label == '12'
    assert connector.socket == 'C19'
    assert connector.custom_label == 'foo'


def test_sensor_object():
    uid = 'unqiue_id'
    sensor_interface = SENSORS_NUMERIC[0]
    sensor_metric = SENSORS_TYPES[1]
    sensor_unit = SENSORS_UNITS[2]
    longname = 'raritan_sensors_%s_in_%s' \
               % (struct.camel_to_snake(sensor_metric),
                  struct.camel_to_snake(sensor_unit))

    sensor = struct.Sensor(
        rid=uid,
        interface=sensor_interface
    )
    sensor.update(type=1, unit=2)
    sensor.set_value(12.34, time.time())

    assert sensor.metric == sensor_metric
    assert sensor.unit == sensor_unit
    assert sensor.name == sensor_metric
    assert sensor.longname == longname
    assert sensor.value == 12.34


def test_metric_object():
    sensor = struct.Sensor(rid='foo', interface=SENSORS_NUMERIC[0])
    sensor.longname = 'foo'
    sensor2 = struct.Sensor(rid='bar', interface=SENSORS_NUMERIC[0])
    sensor2.longname = 'bar'
    metric = struct.Metric(sensor)
    metric.add(sensor2)

    assert metric.sensors[0] == sensor
    assert metric.sensors[1] == sensor2
    assert metric.sensors[0].rid == 'foo'
    assert metric.sensors[1].rid == 'bar'
    assert metric.interface == SENSORS_NUMERIC[0]
    assert metric.name == 'foo'


def test_parent_chaining():
    # TODO: test sensor.parent.parent to get PDU data.
    pass
