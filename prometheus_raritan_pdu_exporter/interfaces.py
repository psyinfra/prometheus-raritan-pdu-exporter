from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from typing import Optional, Union, List, Dict, Any
from aiohttp.client_exceptions import ClientConnectorError
import logging
import re

from . import (
    logger, EXPORTER_PREFIX, SENSORS_TYPES, SENSORS_UNITS,
    SENSORS_DESCRIPTION, SENSORS_GAUGES, SENSORS_COUNTERS)
from .jsonrpc import Request, RaritanAuth, EmptyResponse
from .debug import debug_responses, debug_responses_named


class InterfaceError(Exception):
    def __init__(self, target: Sensor):
        message = f'Unusable interface for {target}'
        super().__init__(message)


class MetricMismatchError(Exception):
    def __init__(self, family: MetricFamily, metric: Metric):
        message = f'Metric {metric} cannot be added to {family}'
        super().__init__(message)


@dataclass
class PDU:
    auth: RaritanAuth = field(repr=False)

    name: str = field(init=False)
    connectors: list[Connector] = field(
        default_factory=list, init=False, repr=False)
    poles: list[Pole] = field(default_factory=list, init=False, repr=False)
    sensors: list[Sensor] = field(default_factory=list, init=False, repr=False)

    n_inlets: int = field(init=False, default=0)
    n_outlets: int = field(init=False, default=0)
    n_sensors: int = field(init=False, default=0)
    n_devices: int = field(init=False, default=0)
    n_poles: int = field(init=False, default=0)

    def __post_init__(self):
        super().__setattr__('name', self.auth.name)

    async def setup(self):
        try:
            await self._connectors()
            await self._sensors()

            self.n_poles = len(self.poles)
            self.n_sensors = len(self.sensors)
            self.n_inlets = len(
                [c for c in self.connectors if c.type == 'inlet'])
            self.n_outlets = len(
                [c for c in self.connectors if c.type == 'outlet'])
            self.n_devices = len(
                [c for c in self.connectors if c.type == 'device'])
            logger.info(self)
        except ClientConnectorError as e:
            # Ignore PDUs that fail to connect
            logger.warning(e)
            return

    async def read(self, collect_id: str = '-') -> list[Metric]:
        """Request sensor readings"""
        metrics = []
        request = Request(self.auth, collect_id=collect_id)
        for i, sensor in enumerate(self.sensors):
            request.add(rid=sensor.rid, method='getReading', id=i)

        try:
            result = await request.send()
        except Exception as exc:
            logger.error(
                f'({self.name}#{collect_id}) Uncaught Exception: {exc}')
        else:
            # note: EmptyResponse return value is fine during reads
            if len(self.sensors) > len(result.responses):
                logger.debug(
                    f'({self.name}#{collect_id}) API request returned '
                    f'{len(result.responses)} readings for '
                    f'{self.n_sensors} known sensors')

            for resp in result.responses:
                metric = Metric(
                    sensor=self.sensors[int(resp.id)],
                    value=resp.ret['value'],
                    timestamp=resp.ret['timestamp'])
                metrics.append(metric)

            # Debug: No responses received for these sensors
            if logging.DEBUG >= logger.level:
                debug_responses(
                    requests=[s.name for s in self.sensors],
                    response_ids=[resp.id for resp in result.responses],
                    collect_id=collect_id)

        return metrics

    async def _connectors(self) -> None:
        connectors = await self._connector_rids()
        connectors = await self._connector_metadata(connectors)
        connectors = await self._connector_settings(connectors)
        self.connectors = [Connector(**c) for c in connectors]

    async def _sensors(self) -> None:
        if len(self.connectors) == 0:
            raise ValueError('Cannot get sensors without connector meta-data')

        sensors_pole = await self._sensors_from_poles()
        sensors_con = await self._sensors_from_connectors(self.connectors)
        sensors = [*sensors_pole, *sensors_con]
        sensors = await self._sensor_metadata(sensors)
        self.sensors = [Sensor(**sensor) for sensor in sensors]

    async def _connector_rids(self) -> List[Dict[str, Any]]:
        """get connector rids"""
        request = Request(self.auth)
        request.add(rid='/model/pdu/0', method='getInlets', id='inlet')
        request.add(rid='/model/pdu/0', method='getOutlets', id='outlet')
        request.add(
            rid='/model/peripheraldevicemanager', method='getDeviceSlots',
            id='device')

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        connectors = [
            dict(pdu=self, rid=response.ret['rid'], type=response.id)
            for response in result.responses]

        # Debug: No responses received for these connectors
        if logging.DEBUG >= logger.level:
            debug_responses_named(
                requests=['inlet', 'outlet', 'device'],
                response_ids=[resp.id for resp in result.responses])

        return connectors

    async def _connector_metadata(
            self, connectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        request = Request(self.auth)
        for i, c in enumerate(connectors):
            if c['type'] == 'device':  # devices have no metadata
                continue
            request.add(rid=c['rid'], method='getMetaData', id=i)

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        for resp in result.responses:
            connectors[resp.id]['id'] = resp.ret.get('label', None)

        # Debug: No responses received for these connectors
        if logging.DEBUG >= logger.level:
            debug_responses(
                requests=[
                    c['rid'].rsplit('/', 1)[-1] for c in connectors
                    if c['type'] != 'device'],
                response_ids=[resp.id for resp in result.responses])

        return connectors

    async def _connector_settings(
            self, connectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        request = Request(self.auth)
        for i, c in enumerate(connectors):
            request.add(rid=c['rid'], method='getSettings', id=i)

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        for resp in result.responses:
            connectors[resp.id]['name'] = resp.ret.get('name', None)

        # Debug: No responses received for these connectors
        if logging.DEBUG >= logger.level:
            from .debug import debug_responses
            debug_responses(
                requests=[c['rid'] for c in connectors],
                response_ids=[resp.id for resp in result.responses])

        return connectors

    async def _sensors_from_poles(self) -> List[Dict[str, Any]]:
        sensors = []
        poles = []
        inlets = [c for c in self.connectors if c.type == 'inlet']
        request = Request(self.auth)

        for i, c in enumerate(inlets):
            request.add(rid=c.rid, method='getPoles', id=i)

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        for resp in result.responses:
            poles.append(Pole(
                pdu=self, name=resp.ret['label'], id=resp.ret['nodeId']))

            for name, ret in resp.ret.items():
                non_metrics = ['label', 'line', 'nodeId']
                if name not in non_metrics and ret is not None:
                    sensors.append(
                        dict(rid=ret['rid'], interface=ret['type'],
                             parent=poles[-1], name=name))

        self.poles = poles

        # Debug: No responses received for these connectors
        if logging.DEBUG >= logger.level:
            debug_responses(
                requests=[c.name for c in inlets],
                response_ids=[resp.id for resp in result.responses])

        return sensors

    async def _sensors_from_connectors(
            self, connectors: List[Connector]) -> List[Dict[str, Any]]:
        sensors = []
        methods = {
            'inlet': 'getSensors', 'outlet': 'getSensors',
            'device': 'getDevice'}
        request = Request(self.auth)
        for i, c in enumerate(connectors):
            request.add(rid=c.rid, method=methods[c.type], id=i)

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        for resp in result.responses:
            connector = connectors[resp.id]
            if connector.type == 'device':
                if resp.ret is None:
                    continue

                ret = resp.ret.get('value', {}).get('device', None)
                base_type = ret.get('type', '').split(':')[0]
                if base_type not in [*SENSORS_GAUGES, *SENSORS_COUNTERS]:
                    # ignore state sensors
                    continue

                sensors.append(dict(
                    rid=ret['rid'], interface=ret['type'], parent=connector))

            elif connector.type in ['inlet', 'outlet']:
                for name, ret in resp.ret.items():
                    if ret is None:
                        continue

                    base_type = ret.get('type', '').split(':')[0]
                    if base_type not in [*SENSORS_GAUGES, *SENSORS_COUNTERS]:
                        # ignore state sensors
                        continue

                    sensors.append(dict(
                        rid=ret['rid'], interface=ret['type'],
                        parent=connector, name=name))

        # Debug: No responses received for these connectors
        if logging.DEBUG >= logger.level:
            debug_responses(
                requests=[c.name for c in connectors],
                response_ids=[resp.id for resp in result.responses])

        return sensors

    async def _sensor_metadata(
            self, sensors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """get sensor metadata"""
        request = Request(self.auth)
        for i, sensor in enumerate(sensors):
            request.add(rid=sensor['rid'], method='getMetaData', id=i)

        result = await request.send()
        if isinstance(result, EmptyResponse):
            # EmptyResponses are not acceptable during setup
            raise result.exception

        for resp in result.responses:
            ret = resp.ret.get('type', {})
            sensors[resp.id]['metric'] = ret.get('type', 0)
            sensors[resp.id]['unit'] = ret.get('unit', 0)

        # Debug: No responses received for these sensors
        if logging.DEBUG >= logger.level:
            debug_responses(
                requests=[s['rid'].rsplit('/', 1)[-1] for s in sensors],
                response_ids=[resp.id for resp in result.responses])

        return sensors


@dataclass(frozen=True)
class Connector:
    pdu: PDU
    rid: str
    id: str = field(default=None)
    name: Optional[str] = field(default=None)
    type: str = field(default='connector')

    def __post_init__(self) -> None:
        if self.id is None:
            super().__setattr__('id', self.rid.rsplit('/', 1)[-1])

        if self.name is None or self.name in ["''", '']:
            super().__setattr__('name', self.id)


@dataclass(frozen=True)
class Pole:
    pdu: PDU
    id: Union[str, int]
    name: Optional[str] = field(default=None)
    type: str = field(init=False, default='pole')

    def __post_init__(self):
        if self.name is None or self.name in ["''", '']:
            super().__setattr__('name', f'L{self.id}')


@dataclass(frozen=True)
class Sensor:
    rid: str
    interface: str
    metric: InitVar[int] = field(default=0)
    unit: InitVar[int] = field(default=0)
    name: str = field(default=None)
    parent: Union[Pole, Connector] = field(default=None)

    def __post_init__(self, metric: int, unit: int):
        metric = SENSORS_TYPES[metric] if self.name is None else self.name
        metric = metric.lower()
        unit = SENSORS_UNITS[unit]
        name = f"{EXPORTER_PREFIX}_{metric}{'_'+unit if unit else ''}"
        interface = self.interface.split(':')[0]  # remove sensor version

        if interface in SENSORS_GAUGES:
            super().__setattr__('interface', 'gauge')
        elif interface in SENSORS_COUNTERS:
            super().__setattr__('interface', 'counter')
            name += '_total'
        else:
            raise InterfaceError(self)

        super().__setattr__('name', name)

        if metric == 'unspecified':
            logger.debug(f'Sensor \'{self.name}\' is of unspecified type')

    @staticmethod
    def camel_to_snake(label: str) -> str:
        """Convert camelCase strings to snake_case"""
        label = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', label)
        label = re.sub('([a-z0-9])([A-Z])', r'\1_\2', label).lower()
        return label


@dataclass
class Metric:
    sensor: InitVar[Sensor]
    value: Union[int, float]
    timestamp: Union[int, float]

    name: str = field(init=False)
    interface: str = field(init=False)
    pdu: str = field(init=False)
    pdu_name: str = field(init=False, repr=False)
    label: str = field(init=False)
    type: str = field(init=False)
    connector_id: str = field(init=False)
    sensor_rid: str = field(init=False, repr=False)

    def __post_init__(self, sensor: Sensor):
        """Extract properties from Sensor"""
        # properties used for label values must be of type str
        self.name = str(sensor.name)
        self.interface = str(sensor.interface)
        self.pdu = str(sensor.parent.pdu.name)
        self.label = str(sensor.parent.name)
        self.type = str(sensor.parent.type)
        self.connector_id = str(sensor.parent.id)
        self.sensor_rid = str(sensor.rid)

    @property
    def is_numeric(self) -> bool:
        if isinstance(self.value, (int, float)):
            return True
        logger.debug(
            f'({self.pdu}) Sensor {self.name} does '
            f'not have a numeric value: \'{self.value}\'')
        return False


@dataclass
class MetricFamily:
    metric: InitVar[Metric]
    name: str = field(init=False)
    interface: str = field(init=False)
    description: str = field(init=False, default='none')
    metrics: list = field(init=False, default_factory=list)

    def __post_init__(self, metric: Metric):
        self.name = metric.name
        self.interface = metric.interface
        self.description = SENSORS_DESCRIPTION.get(self.name, 'none')
        self.metrics.append(metric)

    def add(self, m: Metric):
        if m.name == self.name and m.interface == self.interface:
            self.metrics.append(m)
            return

        raise MetricMismatchError(self, m)
