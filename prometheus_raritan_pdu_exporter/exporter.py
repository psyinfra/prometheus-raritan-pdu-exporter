from typing import List
import asyncio
import random
import string
import time

from prometheus_client import Summary
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily

from . import logger
from .interfaces import PDU, MetricFamily
from .jsonrpc import RaritanAuth


# Measure collection time
REQUEST_TIME = Summary(
    'raritan_collector_collect_seconds',
    'Time spent to collect metrics from the Raritan PDU')


class RaritanExporter:
    def __init__(self, config: List[RaritanAuth]) -> None:
        self.pdus = [PDU(auth=auth) for auth in config]
        asyncio.run(self._setup())

    async def _setup(self):
        await asyncio.gather(*[pdu.setup() for pdu in self.pdus])

    async def _read(self, collect_id: str = '-'):
        return await asyncio.gather(
            *[pdu.read(collect_id=collect_id) for pdu in self.pdus])

    def read(self, collect_id: str = '-') -> List[MetricFamily]:
        pdus = asyncio.run(self._read())
        metrics = [metric for metrics in pdus for metric in metrics]

        # group metrics by family
        metric_family = dict()
        for metric in metrics:
            if metric.name in metric_family.keys():
                metric_family[metric.name].add(metric)
            else:
                metric_family[metric.name] = MetricFamily(metric)

        return list(metric_family.values())

    @REQUEST_TIME.time()
    def collect(self):
        """Collect sensor readings, called every time the http server
        containing the Raritan PDU metrics is requested"""
        collect_id = ''.join(
            random.SystemRandom().choice(
                string.ascii_letters + string.digits) for _ in range(6))
        logger.debug(f'(#{collect_id}) received collect request')
        start = time.time()
        readings = self.read(collect_id=collect_id)
        labels = ['pdu', 'label', 'type', 'connector_id']

        # Debug collection
        n_families = len(readings)
        n_metrics = sum([len(family.metrics) for family in readings])
        n_gauges, n_counters, n_null, n_yields = (0, 0, 0, 0)

        for family in readings:
            if family.interface == 'gauge':
                g = GaugeMetricFamily(
                    family.name, family.description, labels=labels)
                n_gauges += len(family.metrics)
            elif family.interface == 'counter':
                g = CounterMetricFamily(
                    family.name, family.description, labels=labels)
                n_counters += len(family.metrics)
            else:
                continue

            for metric in family.metrics:
                if not metric.is_numeric:
                    n_null += 1
                    continue

                g.add_metric([
                    metric.pdu, metric.label, metric.type,
                    metric.connector_id], metric.value)

            yield g
            n_yields += 1

        end = time.time()
        logger.debug(
            f"(#{collect_id}) completed collect with {n_yields}/{n_families} "
            f"yields containing {n_counters + n_gauges + n_null}/"
            f"{n_metrics} metrics ({n_counters} counter{'s'[:n_counters^1]}, "
            f"{n_gauges} gauge{'s'[:n_counters^1]}, {n_null} "
            f"null{'s'[:n_counters^1]}) in {end - start:.2f}s")
