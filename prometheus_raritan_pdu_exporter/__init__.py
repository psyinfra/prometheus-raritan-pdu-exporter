import logging

logging.basicConfig(
    level=logging.CRITICAL, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger('prometheus_raritan_pdu_exporter')

# Prefix for the Prometheus metrics
EXPORTER_PREFIX = 'raritan_pdu'

# Default port used by the Raritan PDU Exporter
DEFAULT_PORT = 9840

# All sensor interfaces that are to be recorded as prometheus gauges
SENSORS_GAUGES = [
    'sensors.NumericSensor:4.0.3',
    'pdumodel.TypeBResidualCurrentNumericSensor:1.0.2']

# All sensor interfaces that are to be recorded as prometheus counters
SENSORS_COUNTERS = ['sensors.AccumulatingNumericSensor:2.0.3']

# Contains all the available sensor types. The order of this list is
# important, as the list-id is referenced by the pdumodel metadata output
SENSORS_TYPES = [
    'unspecified', 'voltage', 'current', 'unbalance_current', 'power',
    'power_factor', 'energy', 'frequency', 'temperature', 'humidity',
    'air_flow', 'air_pressure', 'contact_closure', 'on_off_sensor',
    'trip_sensor', 'vibration', 'water_leak', 'smoke_detector',
    'total_harmonic_distortion', 'mass', 'electrical_resistance', 'flux',
    'luminous_intensity', 'acceleration', 'magnetic_flux_density',
    'electric_field_strength', 'magnetic_field_strength', 'angle',
    'selection', 'fault_state', 'power_quality', 'rotational_speed',
    'luminous_energy', 'luminous_flux', 'illuminance', 'luminous_emittance',
    'motion', 'occupancy', 'tamper', 'dry_contact', 'powered_dry_contact',
    'absolute_humidity', 'door_state', 'door_lock_state', 'door_handle_lock',
    'crest_factor']

# All available units of measurement. As with SENSORS_TYPES, the order
# is important for the same reason.
SENSORS_UNITS = [
    None, 'volt', 'ampere', 'watt', 'volt_amp', 'watt_hour',
    'volt_amp_hour', 'degree_celsius', 'hz', 'percent', 'meter_per_sec',
    'pascal', 'g', 'rpm', 'meter', 'hour', 'minute', 'second',
    'volt_amp_reactive', 'volt_amp_reactive_hour', 'gram', 'ohm',
    'liters_per_hour', 'candela', 'meter_per_square_sec', 'tesla',
    'volt_per_meter', 'volt_per_ampere', 'degree', 'degree_fahrenheit',
    'kelvin', 'joule', 'coulomb', 'nit', 'lumen', 'lumen_second', 'lux',
    'psi', 'newton', 'foot', 'foot_per_sec', 'cubic_meter', 'radiant',
    'steradiant', 'henry', 'farad', 'mol', 'becquerel', 'gray', 'sievert',
    'g_per_cubic_meter']

# Optional description per sensor
SENSORS_DESCRIPTION = {
    f'{EXPORTER_PREFIX}_voltage_volt':
        'RMS voltage between this phase and the next',
    f'{EXPORTER_PREFIX}_voltage_ln_volt':
        'RMS voltage between the phase and the neutral/earth potential',
    f'{EXPORTER_PREFIX}_current_ampere':
        'RMS current',
    f'{EXPORTER_PREFIX}_residual_current_ampere':
        'Residual current',
    f'{EXPORTER_PREFIX}_residual_dc_current_ampere':
        'Residual DC current',
    f'{EXPORTER_PREFIX}_active_power_watt':
        'Active power',
    f'{EXPORTER_PREFIX}_apparent_power_volt_amp':
        'Apparent Power',
    f'{EXPORTER_PREFIX}_power_factor':
        'Total power factor (no unit)',
    f'{EXPORTER_PREFIX}_active_energy_watt_hour_total':
        'Active energy counter',
    f'{EXPORTER_PREFIX}_unbalanced_current_percent':
        'Maximum difference between the three phase current readings and the '
        'average current reading',
    f'{EXPORTER_PREFIX}_line_frequency_hz':
        'Line frequency',
    f'{EXPORTER_PREFIX}_temperature_degree_celsius':
        'Measured temperature',
    f'{EXPORTER_PREFIX}_humidity_percent':
        'Measured humidity',
    f'{EXPORTER_PREFIX}_absolute_humidity_g_per_cubic_meter':
        'Measured absolute humidity'}

__all__ = [
    logger, EXPORTER_PREFIX, DEFAULT_PORT, SENSORS_GAUGES, SENSORS_COUNTERS,
    SENSORS_TYPES, SENSORS_UNITS, SENSORS_DESCRIPTION]
