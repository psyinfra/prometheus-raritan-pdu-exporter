from raritan_globals import (SENSORS_TYPES, SENSORS_UNITS, SENSORS_NUMERIC, 
    SENSORS_STATE, RARITAN_GAUGES, RARITAN_COUNTERS)
from prometheus_client import start_http_server, Gauge, Counter, REGISTRY
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily
from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request
from urllib.parse import urljoin, urlparse
from typing import Optional, List
import threading
import urllib3
import logging
import time
import json
import sys
import re

# Raritan PDU has no SSL certificate, ignore the ensuing warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# External (root level) logging level
logging.basicConfig(level=logging.WARNING)

# Internal logging level
logger = logging.getLogger('raritan_exporter')
logger.setLevel(level=logging.WARNING)


def camel_to_snake(label: str) -> str:
    """Convert camelCase strings to snake_case"""
    label = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', label)
    label = re.sub('([a-z0-9])([A-Z])', r'\1_\2', label).lower()
    return label


class PDU(object):
    """Raritan power distribution unit (PDU) data object.

    Sets up a connection to the bulk json-rpc interface for Raritan PDUs and
    requests all connectors (inlets, outlets, and device slots) and their
    respective sensors. Sensors can subsequently be read to obtain up-to-date
    values.

    Parameters
    ----------
    name : str
        name of the PDU. Only used for logging purposes.
    location : str
        Internet address of the PDU, including the protocol (e.g., http:// or
        https://)
    auth : tuple, optional
        the username and password combination for logging into the PDU from 
        its internet address
    verify : bool, optional
        whether the SSL certificate of the connection has to be verified
    """
    def __init__(self, name: str, location: str,
                 auth: Optional[tuple] = (), verify: Optional[bool] = False):
        self.name = name
        self.location = urlparse(location).netloc
        self.uri_pdu = '/model/pdu/0'
        self.uri_device = '/model/peripheraldevicemanager'
        self.client = self._http_client(endpoint = urljoin(location, '/bulk'), 
                auth = auth, verify = verify)
        self.connectors = []
        self.sensors = []

    def _http_client(self, endpoint: str,
                    auth: Optional[tuple] = (),
                    verify: Optional[bool] = False) -> HTTPClient:
        """Set up an HTTP client for json-rpc requests"""
        logger.info('(%s) configuring HTTP client to %s' % (self.name,
            endpoint))
        client = HTTPClient(endpoint)
        client.session.auth = auth
        client.session.verify = verify
        client.session.headers.update({"Content-Type": "application/json-rpc"})
        return client

    def get_sources(self):
        """request all sources (connectors and their sensors) from the PDU"""
        logger.info('(%s) requesting connectors' % self.name)
        requests = {'requests': [
            {'rid': self.uri_pdu, 
             'json': Request('getInlets', request_id='inlet')},
            {'rid': self.uri_pdu, 
             'json': Request('getOutlets', request_id='outlet')},
            {'rid': self.uri_device, 
             'json': Request('getDeviceSlots', request_id='device')},
        ]}
        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']
        self.connectors = [
            Connector(rid=ret['rid'], type_=resp['json']['id'], parent=self)
            for resp in responses
            for ret in resp['json']['result']['_ret_']
        ]
        logger.info('(%s) %s connectors found' 
            % (self.name, len(self.connectors)))
        logger.info('(%s) retrieving metadata per connector' % self.name)
        requests = {'requests': [
            {'rid': c.rid, 'json': Request('getMetaData', request_id=i)}
            for i, c in enumerate(self.connectors)
            if c.type != 'device'  # devices have no metadata
        ]}
        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            connector = self.connectors[resp['json']['id']]
            connector.update(**resp['json']['result']['_ret_'])

        logger.info('(%s) requesting sensors for each connector' % self.name)
        requests = {'requests': []}
        for i, c in enumerate(self.connectors):
            if c.type == 'inlet' or c.type == 'outlet':
                method = 'getSensors'
            elif c.type == 'device':
                method = 'getDevice'

            requests['requests'].append(
                {'rid': c.rid, 'json': Request(method, request_id=i)}
            )

        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            connector = self.connectors[resp['json']['id']]
            ret = resp['json']['result']['_ret_']

            if connector.type is 'device':  # one sensor only
                rid = ret['value']['device']['rid']
                type_ = ret['value']['device']['type']
                self.sensors.append(Sensor(rid, type_, connector))

            elif connector.type in ['inlet', 'outlet']:  # multiple sensors
                for metric, data in ret.items():
                    if data is None:  # unused sensors return None
                        continue

                    rid = data['rid']
                    type_ = data['type']
                    self.sensors.append(Sensor(rid, type_, connector, metric))

        logger.info('(%s) %s sensors found' % (self.name, len(self.sensors)))

        logger.info('(%s) retrieving metadata per sensor' % self.name)
        requests = {'requests': [
            {'rid': s.rid, 'json': Request('getMetaData', request_id=i)}
            for i, s in enumerate(self.sensors)
            if s.interface not in SENSORS_STATE  # these have no metadata
        ]}
        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            sensor = self.sensors[resp['json']['id']]
            sensor.update(**resp['json']['result']['_ret_'])

    def read_sensors(self):
        """Bulk request to read all sensors"""
        requests = {'requests': []}
        for sensor_id, sensor in enumerate(self.sensors):
            if sensor.interface in SENSORS_NUMERIC:
                method = 'getReading'
            elif sensor.interface in SENSORS_STATE:
                method = 'getState'
            else:
                continue  # unlisted interface

            requests['requests'].append({
                'rid': sensor.rid,
                'json': Request(method, request_id=sensor_id)
            })

        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            sensor_id = resp['json']['id']
            sensor = self.sensors[int(sensor_id)]
            value = resp['json']['result']['_ret_']['value']
            timestamp = resp['json']['result']['_ret_']['timestamp']
            sensor.set_value(value, timestamp)

    def clear_sensor_values(self):
        """Clear the readings of all the sensors"""
        for sensor in self.sensors:
            sensor.set_value(None, None)


class Connector(object):
    """Stores connector (inlet, outlet, or device slot) data.
    
    Parameters
    ----------
    rid : str
        RID of the connector, returned by a json-rpc request for the 
        getInlets, getOutlets, or getDeviceSlots methods to their respective
        URIs
    type_ : str
        The connector type (either inlet, outlet, or device)
    parent : PDU, optional
        The PDU object this connector belongs to
    """
    def __init__(self, rid: str, type_: str, parent: Optional[PDU] = None):
        self.rid = rid
        self.type = type_
        self.parent = parent
        self.socket = None  # plug or receptacle
        self.label = rid.rsplit('/', 1)[-1].rsplit('.', 1)[-1]

    def update(self, **kwargs: dict):
        """update the connector object with meta data"""
        if kwargs.get('label', None):
            self.label = kwargs['label']

        if self.type == 'outlet':
            self.socket = kwargs.get('receptacleType', None)
        elif self.type == 'inlet':
            self.socket = kwargs.get('plugType', None)


class Sensor(object):
    """Stores sensor data.

    Parameters
    ----------
    rid : str
        RID of hte sensor, returned by a json-rpc request for the getSensors
        and getDevice methods to their respective URIs
    interface : str
        The interface type of the sensor (e.g. numeric, state, accumulative
        numeric, etc.) in the format returned by the Raritan PDU
    name : str, optional
        Name given to a sensor from a connector with multiple sensors. Note
        that device slots only return one device, hence not naming the
        sensor and making this parameter optional
    metric : str, optional
        Metric name as returned from the sensor meta data. Note that connectors
        with multiple sensors may have sensors that share a metric name, hence
        requiring the name parameter to create a unique long name for
        prometheus collection
    unit : str, optional
        The unit of measurement of the metric as returned from the sensor
        meta data
    """
    def __init__(self, rid: str, interface: str,
                 parent: Optional[Connector] = None, 
                 name: Optional[str] = None,
                 metric: Optional[str] = 'unspecified', 
                 unit: Optional[str] = 'none'):
        self.rid = rid
        self.interface = interface
        self.parent = parent
        self.name = name
        self.metric = metric
        self.unit = unit
        self.longname = None
        self.value = None
        self.timestamp = None

    def update(self, **kwargs: dict):
        """Update the sensor object with meta data"""
        self.metric = SENSORS_TYPES[kwargs.get('type', {}).get('type', 0)]
        self.unit = SENSORS_UNITS[kwargs.get('type', {}).get('unit', 0)]

        if self.name is None:
            self.name = self.metric

        self.longname = 'raritan_sensors_%s' % camel_to_snake(self.name)

        if self.unit not in (None, 'none'):
            self.longname = '%s_in_%s' % (self.longname,
                camel_to_snake(self.unit))

    def set_value(self, 
                  value: Optional[float] = None, 
                  timestamp: Optional[int] = None):
        """Set the value of the sensor as obtained from a reading"""
        self.value = value
        self.timestamp = timestamp


class Metric(object):
    """Stores metric data.

    PDU data is hierarchically structured as PDU > Connector > Sensor, but
    for ease of collection this object helps reorganize and group sensors by 
    their metrics. Hence, each metric object consists of multiple sensors that
    measure the same thing regardless of which connector or PDU the sensor
    belongs to.

    Parameters
    ----------
    sensor : Sensor
        The Sensor object that initiates the Metric object. All data that
        metrics share (e.g. unit, interface, and longname) is taken from this
        sensor.
    """
    def __init__(self, sensor: Sensor):
        self.name = None
        self.interface = None
        self.unit = None
        self.description = 'none'  # TODO: add descriptions
        self.sensors = []
        self.add(sensor)

    def add(self, sensor: Sensor):
        if self.unit is None:
            self.unit = sensor.unit

        if self.interface is None:
            self.interface = sensor.interface

        if self.name is None:
            self.name = sensor.longname

        self.sensors.append(sensor)


class RaritanExporter:
    """Prometheus exporter for Raritan PDUs
    
    Parameters
    ----------
    config : str
        Path to the configuration file, containing PDU location, username,
        and password combinations for all PDUs to be monitored
    threading : bool, optional
        Whether to use multithreading or serial processing. Note that serial
        processing becomes slower when more PDUs are added. Since the HTTP
        request to the json-rpc API and waiting for its response takes longest,
        threading is recommended when more than 1 PDU is being monitored
    """
    def __init__(self, config: str, threading: bool = True):
        self.counter = 0
        self.threading = threading
        self.pdus = self.get_pdus(config)

    def get_pdus(self, config: str) -> list:
        """Set up all PDUs found in the configuration file"""
        with open(config) as json_file:
            data = json.load(json_file)

        pdus = [PDU(k, v['instance'], (v['user'], v['password']), False)
                for k, v in data.items()]

        if self.threading:
            threads = []
            for pdu in pdus:
                thread = threading.Thread(target=pdu.get_sources)
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for pdu in pdus:
                pdu.get_sources()

        return pdus

    def get_reading(self) -> List[Metric]:
        """Obtain a sensor reading for all sensors from all PDUs"""
        if self.threading:
            threads = []
            for pdu in self.pdus:
                thread = threading.Thread(target=pdu.read_sensors)
                threads.append(thread)

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        else:
            for pdu in self.pdus:
                pdu.read_sensors()

        # convert all PDU.Sensors to Metric format
        metrics = []
        for pdu in self.pdus:
            for sensor in pdu.sensors:
                name = sensor.longname
                keys = [m.name for m in metrics]
                metric_id = keys.index(name) if name in keys else None

                if metric_id is not None:
                    metrics[metric_id].add(sensor)
                else:
                    metrics.append(Metric(sensor))

        return metrics

    def diagnose(self, failures: Optional[list] = []):
        """Diagnose acquisition issues when the logging level is set to 
        DEBUG"""
        if not failures:
            return

        data = {}
        for pdu, sensor in failures:
            if pdu in data.keys():
                data[pdu].append(sensor)
            else:
                data[pdu] = [sensor]

        logger.debug('Failed to update %s' % ', '.join(data.keys()))

        pdu_ids = [pdu.name for pdu in self.pdus]

        for pdu_id, failed_sensors in data.items():
            all_sensors = self.pdus[pdu_ids.index(pdu_id)].sensors
            numeric_sensors = [sensor.rid for sensor in all_sensors
                               if sensor.interface in SENSORS_NUMERIC]
            state_sensors = [sensor.rid for sensor in all_sensors
                             if sensor.interface in SENSORS_STATE]

            failed_numeric = [sensor for sensor in failed_sensors
                              if sensor in numeric_sensors]
            failed_state = [sensor for sensor in failed_sensors
                            if sensor in state_sensors]

            if failed_numeric:
                logger.debug('(%s) failed to update %s out of %s numeric ' \
                    'sensors' % (pdu_id, len(failed_numeric), 
                        len(numeric_sensors)))

            if failed_state:
                logger.debug('(%s) failed to update %s out of %s state sensors'
                    % (pdu_id, len(failed_state), len(state_sensors)))


    def collect(self):
        """Collect sensor readings, called every time the http server 
        containing the Raritan PDU metrics is requested"""
        start = time.time()

        for pdu in self.pdus:
            pdu.clear_sensor_values()

        metrics = self.get_reading()
        labels = ['instance', 'label', 'type']  # TODO: flesh out labels
        failures = []

        # Expose all metrics
        for metric in metrics:
            if metric.interface in RARITAN_GAUGES:
                g = GaugeMetricFamily(
                    metric.name, 
                    metric.description, 
                    labels=labels
                )
                for sensor in metric.sensors:
                    if sensor.value is None:
                        if logger.level <= logging.DEBUG:
                            failures.append((sensor.parent.parent.name,
                                sensor.rid))
                        continue

                    g.add_metric(
                        [sensor.parent.parent.location, 
                         sensor.parent.label,
                         sensor.parent.type],
                        sensor.value
                    )

            elif metric.interface in RARITAN_COUNTERS:
                g = CounterMetricFamily(
                    metric.name, 
                    metric.description, 
                    labels=labels
                )
                for sensor in metric.sensors:
                    if sensor.value is None:
                        if logger.level <= logging.DEBUG:
                            failures.append((sensor.parent.parent.name,
                                sensor.rid))
                        continue

                    g.add_metric(
                        [sensor.parent.parent.location, 
                         sensor.parent.label,
                         sensor.parent.type],
                        sensor.value
                    )

            else:  # interface cannot be collected (i.e., state sensors)
                continue

            yield g

        end = time.time()
        elapsed = round(end - start, 2)

        if self.counter < 1:
            logger.info('initial collection of sensor readings in %ss'
                % elapsed)
        else:
            logger.info('collected sensor readings #%s in %ss' 
                % (self.counter, elapsed)) 

        if logger.level <= logging.DEBUG:
            self.diagnose(failures)

        self.counter += 1


if __name__ == '__main__':
    logger.info('starting HTTP server on port %s ...' % sys.argv[1])
    start_http_server(int(sys.argv[1]))
    logger.info('adding RaritanExporter to Prometheus client REGISTRY')
    REGISTRY.register(RaritanExporter('config.json', threading = True))

    while True:
        time.sleep(1)

