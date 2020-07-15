from raritan_globals import (SENSORS_NUMERIC, SENSORS_STATE, SENSORS_TYPES,
    SENSORS_UNITS)
from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request
from urllib.parse import urljoin, urlparse
from typing import Optional, List
import logging
import re

# Internal logging
logger = logging.getLogger('raritan_exporter')

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
    insecure : bool, optional
        whether to allow an insecure connection to the raritan PDU
    """
    def __init__(self, location: str, name: Optional[str] = None,
                 auth: Optional[tuple] = (), insecure: Optional[bool] = True):
        self.location = urlparse(location).netloc
        self.name = name if name is not None else self.location
        self.uri_pdu = '/model/pdu/0'
        self.uri_device = '/model/peripheraldevicemanager'
        self.client = self._http_client(endpoint = urljoin(location, '/bulk'), 
                auth = auth, verify = not insecure)
        self.connectors = []
        self.sensors = []

    def _http_client(self, endpoint: str,
                    auth: Optional[tuple] = (),
                    verify: Optional[bool] = False) -> HTTPClient:
        """Set up an HTTP client for json-rpc requests"""
        logger.info('(%s) polling at %s' % (self.name,
            endpoint))
        client = HTTPClient(endpoint)
        client.session.auth = auth
        client.session.verify = verify
        client.session.headers.update({"Content-Type": "application/json-rpc"})
        return client

    def get_sources(self):
        """request all sources (connectors and their sensors) from the PDU"""
        # Get connector RIDs
        n_inlets, n_outlets, n_devices, n_sensors = (0, 0, 0, 0)
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

        # Get connector metadata
        requests = {'requests': [
            {'rid': c.rid, 'json': Request('getMetaData', request_id=i)}
            for i, c in enumerate(self.connectors)
            if c.type != 'device'  # devices have no metadata
        ]}
        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            connector = self.connectors[resp['json']['id']]
            connector.update('metadata', **resp['json']['result']['_ret_'])

        # TODO: add update parameter 'method' for  metadata and settings

        # Get connector settings
        requests = {'requests': [
            {'rid': c.rid, 'json': Request('getSettings', request_id=i)}
            for i, c in enumerate(self.connectors)
            if c.type != 'device'  # devices have no settings
        ]}
        response = self.client.send(Request('performBulk', **requests))
        responses = response.data.result['responses']

        for resp in responses:
            connector = self.connectors[resp['json']['id']]
            connector.update('settings', **resp['json']['result']['_ret_'])

        # Get sensors per connector
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

            if connector.type == 'device':  # one sensor only
                if ret is None: # unused device slots return None
                    continue

                rid = ret['value']['device']['rid']
                type_ = ret['value']['device']['type']
                self.sensors.append(Sensor(rid, type_, connector))
                n_devices += 1
                n_sensors += 1

            elif connector.type in ['inlet', 'outlet']:  # multiple sensors
                if connector.type == 'inlet':
                    n_inlets += 1
                elif connector.type == 'outlet':
                    n_outlets += 1

                for metric, data in ret.items():
                    if data is None:  # unused sensors return None
                        continue

                    rid = data['rid']
                    type_ = data['type']
                    self.sensors.append(Sensor(rid, type_, connector, metric))
                    n_sensors += 1

        # Get sensor metadata
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

        logger.info('(%s) %s inlet(s), %s outlet(s), and %s device(s) with ' \
            'a total of %s sensor(s) found' % (self.name, n_inlets, n_outlets,
            n_devices, n_sensors))

    def read_sensors(self):
        """Bulk request to read all sensors"""
        for sensor in self.sensors:
            sensor.set_value(None, None)

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
        self.label = rid.rsplit('/', 1)[-1]
        self.custom_label = None

    def update(self, method: str, **kwargs: dict):
        """update the connector object with meta data"""
        if method == 'metadata':
            if kwargs.get('label', None):
                self.label = kwargs['label']

            if self.type == 'outlet':
                self.socket = kwargs.get('receptacleType', None)
            elif self.type == 'inlet':
                self.socket = kwargs.get('plugType', None)

        elif method == 'settings':
            if kwargs.get('name', None):
                self.custom_label = kwargs['name']


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

