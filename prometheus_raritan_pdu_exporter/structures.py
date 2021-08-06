from typing import Optional, Any, Union
from urllib.parse import urljoin, urlparse, urlunparse
import logging
import time

from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests

from prometheus_raritan_pdu_exporter.globals import (
    SENSORS_NUMERIC, SENSORS_STATE, SENSORS_TYPES, SENSORS_UNITS,
    SENSORS_DESCRIPTION)
from prometheus_raritan_pdu_exporter.utils import camel_to_snake


# Internal logging
logger = logging.getLogger('prometheus_raritan_pdu_exporter')


class PDU(object):
    model_requests = [
        ['/model/pdu/0', 'getInlets', 'inlet'],
        ['/model/pdu/0', 'getOutlets', 'outlet'],
        ['/model/peripheraldevicemanager', 'getDeviceSlots', 'device']]

    def __init__(
            self, location: str, name: Optional[str] = None,
            auth: Optional[tuple] = None, insecure: Optional[bool] = True):
        """Raritan power distribution unit (PDU) data object.

        Sets up a connection to the bulk json-rpc interface for Raritan PDUs
        and requests all connectors (inlets, outlets, and device slots) and
        their respective sensors. Sensors can subsequently be read to obtain
        up-to-date values.

        Parameters
        ----------
        name : str
            name of the PDU. Only used for logging purposes.
        location : str
            Internet address of the PDU, including the protocol (e.g., http://
            or https://)
        auth : tuple, optional
            the username and password combination for logging into the PDU from
            its internet address
        insecure : bool, optional
            whether to allow an insecure connection to the
            Raritan PDU
        """
        if auth is None:
            auth = ()

        self.location = urlparse(location)

        if not self.location.scheme:
            self.location._replace(scheme='http')

        self.name = name if name is not None else self.location.netloc
        self.location = urlunparse(self.location)
        self.connectors = []
        self.poles = []
        self.sensors = []

        # HTTP Client
        logger.info(f'({self.name}) polling at {self.location}')
        client = HTTPClient(urljoin(self.location, '/bulk'))
        client.session.auth = auth
        client.session.verify = not insecure
        client.session.headers.update({"Content-Type": "application/json-rpc"})
        retry = Retry(connect=1)  # max. 1 retry to prevent pool overflows
        adapter = HTTPAdapter(max_retries=retry)
        client.session.mount('http://', adapter)
        client.session.mount('https://', adapter)
        self.client = client

    def send(self, request: Request, **kwargs):
        return self.client.send(request, timeout=10, **kwargs)

    def bulk(self, reqs: list, **kwargs):
        return self.client.send(
            Request('performBulk', requests=reqs), timeout=10, **kwargs)

    def crawl(self):
        """request all sources (connectors and their sensors) from the PDU"""
        self._get_connectors()
        self._get_poles()
        self._get_sensors()

        n_inlets = len([c for c in self.connectors if c.type == 'inlet'])
        n_outlets = len([c for c in self.connectors if c.type == 'outlet'])
        n_devices = len([c for c in self.connectors if c.type == 'device'])
        n_poles = len(self.poles)
        n_sensors = len(self.sensors)
        logger.info(
            '(%s) %s inlet(s), %s outlet(s), %s pole(s) and %s device(s) with '
            'a total of %s sensor(s) found'
            % (self.name, n_inlets, n_outlets, n_poles, n_devices, n_sensors))

    def _get_connectors(self):
        """Find all connectors and retrieve all associated meta-data"""
        # Get connector RIDs
        response = self.bulk([
            {'rid': m[0], 'json': Request(m[1], request_id=m[2])}
            for m in self.model_requests])
        self.connectors = [
            Connector(rid=ret['rid'], type_=resp['json']['id'], parent=self)
            for resp in response.data.result['responses']
            for ret in resp['json']['result']['_ret_']]

        # Get connector metadata
        response = self.bulk([
            {'rid': c.rid, 'json': Request('getMetaData', request_id=i)}
            for i, c in enumerate(self.connectors)
            if c.type != 'device'])  # devices have no metadata

        for resp in response.data.result['responses']:
            self.connectors[
                resp['json']['id']].update(
                    'metadata', **resp['json']['result']['_ret_'])

        # Get connector settings
        response = self.bulk([
            {'rid': c.rid, 'json': Request('getSettings', request_id=i)}
            for i, c in enumerate(self.connectors)])

        for resp in response.data.result['responses']:
            self.connectors[
                resp['json']['id']].update(
                    'settings', **resp['json']['result']['_ret_'])

    def _get_poles(self):
        """Get inlet poles and their associated sensors. This is done
        outside of self._get_sensors due to the different structure of the
        output"""
        # Get pole RIDs
        inlets = [c for c in self.connectors if c.type == 'inlet']
        response = self.bulk([
            {'rid': c.rid, 'json': Request('getPoles', request_id=i)}
            for i, c in enumerate(inlets)])

        for resp in response.data.result['responses']:
            for pole in resp['json']['result']['_ret_']:
                self.poles.append(Pole(
                    label=pole['label'], line=pole['line'],
                    node_id=pole['nodeId'], inlet=inlets[resp['json']['id']],
                    parent=self))

                # Get associated sensors
                for metric, data in pole.items():
                    non_metrics = ['label', 'line', 'nodeId']
                    if metric not in non_metrics and data is not None:
                        self.sensors.append(Sensor(
                            rid=data['rid'], interface=data['type'],
                            parent=self.poles[-1], name=metric))

    def _get_sensors(self):
        """Obtain sensor URI's and meta-data for each connector"""
        # Get sensor RIDs from connectors
        response = self.bulk([
            {'rid': c.rid, 'json': Request(c.get_sensors, request_id=i)}
            for i, c in enumerate(self.connectors)])

        for resp in response.data.result['responses']:
            connector = self.connectors[resp['json']['id']]
            ret = resp['json']['result']['_ret_']

            if connector.type == 'device' and ret is not None:
                # connectors w/ one sensor; returns no data if unused
                self.sensors.append(Sensor(
                    rid=ret['value']['device']['rid'],
                    interface=ret['value']['device']['type'],
                    parent=connector))

            elif connector.type in ['inlet', 'outlet']:
                # connectors w/ multiple sensors; returns none data if unused
                for metric, data in ret.items():
                    if data is not None:
                        self.sensors.append(Sensor(
                            rid=data['rid'], interface=data['type'],
                            parent=connector, name=metric))

        # Get sensor metadata
        response = self.bulk([
            {'rid': s.rid, 'json': Request('getMetaData', request_id=i)}
            for i, s in enumerate(self.sensors)
            if s.interface not in SENSORS_STATE])  # these have no metadata

        for r in response.data.result['responses']:
            self.sensors[
                r['json']['id']].update(**r['json']['result']['_ret_'])

    def clear_sensors(self):
        for sensor in self.sensors:
            sensor.set_value(None, timestamp=time.time())

    def read_sensors(self):
        """Bulk request to read all sensors"""
        for sensor in self.sensors:
            sensor.set_value(None, None)

        query = {'requests': []}
        for sensor_id, sensor in enumerate(self.sensors):
            if sensor.interface in SENSORS_NUMERIC:
                method = 'getReading'
            elif sensor.interface in SENSORS_STATE:
                method = 'getState'
            else:
                continue  # unlisted interface

            query['requests'].append({
                'rid': sensor.rid,
                'json': Request(method, request_id=sensor_id)})

        try:
            response = self.send(Request('performBulk', **query))
            responses = response.data.result['responses']
        except requests.exceptions.ConnectionError as exc:
            logger.warning('(%s) Connection error' % self.name)
            logger.debug(exc)
            self.clear_sensors()  # return None if request failed
        except requests.exceptions.Timeout as exc:
            logger.warning('(%s) Connection timed out' % self.name)
            logger.debug(exc)
            self.clear_sensors()
        except requests.exceptions.TooManyRedirects as exc:
            logger.warning('(%s) Too many redirects' % self.name)
            logger.debug(exc)
            self.clear_sensors()
        except requests.exceptions.RequestException as exc:
            logger.warning('(%s) Unknown error occurred' % self.name)
            logger.debug(exc)
            self.clear_sensors()
        except Exception as exc:
            logger.warning('(%s) Unknown error occurred' % self.name)
            logger.debug(exc)
            self.clear_sensors()
        else:
            for resp in responses:
                sensor_id = resp['json']['id']
                sensor = self.sensors[int(sensor_id)]
                value = resp['json']['result']['_ret_']['value']
                timestamp = resp['json']['result']['_ret_']['timestamp']
                sensor.set_value(value, timestamp)


class Connector(object):
    method_by_type = {
        'inlet': 'getSensors', 'outlet': 'getSensors', 'device': 'getDevice'}

    def __init__(self, rid: str, type_: str, parent: Optional[PDU] = None):
        """Stores connector (inlet, outlet, or device slot) data.

        Parameters
        ----------
        rid : str
            RID of the connector, returned by a json-rpc request for the
            getInlets, getOutlets, or getDeviceSlots methods to their
            respective URIs
        type_ : str
            The connector type (either inlet, outlet, or device)
        parent : PDU, optional
            The PDU object this connector belongs to
        """
        self.rid = rid
        self.type = type_
        self.get_sensors = self.method_by_type[type_]
        self.parent = parent
        self.socket = None  # 'plug' or 'receptacle'
        self.label = rid.rsplit('/', 1)[-1]
        self.custom_label = None

    def update(self, method: str, **kwargs: Any):
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


class Pole(object):
    def __init__(
            self, label: str, line: int, node_id: int,
            inlet: Optional[Connector] = None, parent: Optional[PDU] = None):
        """Stores pole data.

        Unlike other object types, poles don't have an RID. Instead, they
        belong to the Inlet Connector.

        Parameters
        ----------
        type_ : str
            The pole sensor type
        parent : Connector, optional
            The Connector object this pole belongs to
        """
        self.type = 'pole'
        self.label = inlet.label
        self.custom_label = label if label else f'L{line+1}'
        self.line = line
        self.node_id = node_id
        self.inlet = inlet
        self.parent = parent


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
    def __init__(
            self, rid: str, interface: str, parent: Optional[Connector] = None,
            name: Optional[str] = None, metric: Optional[str] = 'unspecified',
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

    def update(self, **kwargs: Any):
        """Update the sensor object with meta data"""
        self.metric = SENSORS_TYPES[kwargs.get('type', {}).get('type', 0)]
        self.unit = SENSORS_UNITS[kwargs.get('type', {}).get('unit', 0)]

        if self.name is None:
            self.name = self.metric

        self.longname = 'raritan_sensors_%s' % camel_to_snake(self.name)

        if self.unit not in (None, 'none'):
            self.longname = '%s_in_%s' % (
                self.longname, camel_to_snake(self.unit))

    def set_value(
            self, value: Optional[float] = None,
            timestamp: Optional[Union[int, float]] = None):
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
        self.description = 'none'
        self.sensors = []
        self.add(sensor)

    def add(self, sensor: Sensor):
        if self.unit is None:
            self.unit = sensor.unit

        if self.interface is None:
            self.interface = sensor.interface

        if self.name is None:
            self.name = sensor.longname

        if self.name in SENSORS_DESCRIPTION.keys():
            self.description = SENSORS_DESCRIPTION[self.name]

        self.sensors.append(sensor)
