import logging

logger = logging.getLogger('prometheus_raritan_pdu_exporter')

# Prefix for the Prometheus metrics
EXPORTER_PREFIX = 'raritanpdu'

# Default port used by the Raritan PDU Exporter
DEFAULT_PORT = 9950

# All sensor interfaces that are to be recorded as prometheus gauges
SENSORS_GAUGES = [
    'sensors.NumericSensor',
    'pdumodel.TypeBResidualCurrentNumericSensor']

# All sensor interfaces that are to be recorded as prometheus counters
SENSORS_COUNTERS = ['sensors.AccumulatingNumericSensor']

# Contains all the available sensor types. The order of this list is
# important, as the list-id is referenced by the pdumodel metadata output
SENSORS_TYPES = [
    'unspecified', 'voltage', 'current', 'unbalancecurrent', 'power',
    'powerfactor', 'energy', 'frequency', 'temperature', 'humidity',
    'airflow', 'airpressure', 'contactclosure', 'onoffsensor',
    'tripsensor', 'vibration', 'waterleak', 'smokedetector',
    'totalharmonicdistortion', 'mass', 'electricalresistance', 'flux',
    'luminousintensity', 'acceleration', 'magneticfluxdensity',
    'electricfieldstrength', 'magneticfieldstrength', 'angle',
    'selection', 'faultstate', 'powerquality', 'rotationalspeed',
    'luminousenergy', 'luminousflux', 'illuminance', 'luminousemittance',
    'motion', 'occupancy', 'tamper', 'drycontact', 'powereddrycontact',
    'absolutehumidity', 'doorstate', 'doorlockstate', 'doorhandlelock',
    'crestfactor']

# All available units of measurement. As with SENSORS_TYPES, the order
# is important for the same reason.
SENSORS_UNITS = [
    None, 'volt', 'ampere', 'watt', 'voltamp', 'watthour',
    'voltamphour', 'degreecelsius', 'hertz', 'percent', 'meterpersec',
    'pascal', 'g', 'rpm', 'meter', 'hour', 'minute', 'second',
    'voltampreactive', 'voltampreactivehour', 'gram', 'ohm',
    'litersperhour', 'candela', 'meterpersquaresec', 'tesla',
    'voltpermeter', 'voltperampere', 'degree', 'degreefahrenheit',
    'kelvin', 'joule', 'coulomb', 'nit', 'lumen', 'lumensecond', 'lux',
    'psi', 'newton', 'foot', 'footpersec', 'cubicmeter', 'radiant',
    'steradiant', 'henry', 'farad', 'mol', 'becquerel', 'gray', 'sievert',
    'gpercubicmeter']

# Optional description per sensor
SENSORS_DESCRIPTION = {
    f'{EXPORTER_PREFIX}_voltage_volt':
        'RMS voltage between this phase and the next',
    f'{EXPORTER_PREFIX}_voltageln_volt':
        'RMS voltage between the phase and the neutral/earth potential',
    f'{EXPORTER_PREFIX}_current_ampere':
        'RMS current',
    f'{EXPORTER_PREFIX}_residualcurrent_ampere':
        'Residual current',
    f'{EXPORTER_PREFIX}_residualdccurrent_ampere':
        'Residual DC current',
    f'{EXPORTER_PREFIX}_activepower_watt':
        'Active power',
    f'{EXPORTER_PREFIX}_apparentpower_voltamp':
        'Apparent Power',
    f'{EXPORTER_PREFIX}_powerfactor':
        'Total power factor (no unit)',
    f'{EXPORTER_PREFIX}_activeenergy_watthour_total':
        'Active energy counter',
    f'{EXPORTER_PREFIX}_unbalancedcurrent_percent':
        'Maximum difference between the three phase current readings and the '
        'average current reading',
    f'{EXPORTER_PREFIX}_linefrequency_hertz':
        'Line frequency',
    f'{EXPORTER_PREFIX}_temperature_degreecelsius':
        'Measured temperature',
    f'{EXPORTER_PREFIX}_humidity_percent':
        'Measured humidity',
    f'{EXPORTER_PREFIX}_absolutehumidity_gpercubicmeter':
        'Measured absolute humidity'}

__all__ = [
    logger, EXPORTER_PREFIX, DEFAULT_PORT, SENSORS_GAUGES, SENSORS_COUNTERS,
    SENSORS_TYPES, SENSORS_UNITS, SENSORS_DESCRIPTION]
