"""
Globals for RaritanExporter
---------------------------
Raritan Python API version 3.6.0

    SENSORS_TYPES : 
        contains all the available sensor types. The order of this list is 
        important, as the list-id is referenced by the pdumodel meta data output
    SENSORS_UNITS :
        all available units of measurement. As with SENSORS_TYPES, the order 
        is important for the same reason.
    SENSORS_NUMERIC :
        all types of numeric sensor (e.g., sensors of which the metrics are 
        recorded as gauges)
    SENSORS_STATE :
        all types of state sensors that (currently) cannot be collected by 
        prometheus
    RARITAN_GAUGES :
        all sensor interfaces that are to be recorded as prometheus gauges
    RARITAN_COUNTERS :
        all sensor interfaces that are to be recorded as prometheus counters

"""

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
SENSORS_UNITS = [
    'none', 'volt', 'ampere', 'watt', 'volt_amp', 'watt_hour',
    'volt_amp_hour', 'degree_celsius', 'hz', 'percent', 'meter_per_sec',
    'pascal', 'g', 'rpm', 'meter', 'hour', 'minute', 'second',
    'volt_amp_reactive', 'volt_amp_reactive_hour', 'gram', 'ohm',
    'liters_per_hour', 'candela', 'meter_per_square_sec', 'tesla',
    'volt_per_meter', 'volt_per_ampere', 'degree', 'degree_fahrenheit',
    'kelvin', 'joule', 'coulomb', 'nit', 'lumen', 'lumen_second', 'lux',
    'psi', 'newton', 'foot', 'foot_per_sec', 'cubic_meter', 'radiant',
    'steradiant', 'henry', 'farad', 'mol', 'becquerel', 'gray', 'sievert',
    'g_per_cubic_meter']
SENSORS_NUMERIC = [
    'sensors.NumericSensor:4.0.3', 
    'pdumodel.TypeBResidualCurrentNumericSensor:1.0.2',
    'sensors.AccumulatingNumericSensor:2.0.3']
SENSORS_STATE = [
    'pdumodel.ResidualCurrentStateSensor:2.0.3', 'sensors.StateSensor:4.0.3']
RARITAN_GAUGES = [
    'sensors.NumericSensor:4.0.3', 
    'pdumodel.TypeBResidualCurrentNumericSensor:1.0.2']
RARITAN_COUNTERS = [
    'sensors.AccumulatingNumericSensor:2.0.3']
SENSORS_DESCRIPTION = {
    'raritan_sensors_voltage_in_volt':
        'RMS voltage between this phase and the next',
    'raritan_sensors_voltage_ln_in_volt':
        'RMS voltage between the phase and the neutral/earth potential',
    'raritan_sensors_current_in_ampere': 'RMS current',
    'raritan_sensors_residual_current_in_ampere': 'Residual current',
    'raritan_sensors_residual_dc_current_in_ampere': 'Residual DC current',
    'raritan_sensors_active_power_in_watt': 'Active power',
    'raritan_sensors_apparent_power_in_volt_amp': 'Apparent Power',
    'raritan_sensors_power_factor': 'Total power factor (no unit)',
    'raritan_sensors_active_energy_in_watt_hour_total':
        'Active energy counter',
    'raritan_sensors_unbalanced_current_in_percent':
        'Maximum difference between the three phase current readings and the '
        'average current reading',
    'raritan_sensors_line_frequency_in_hz': 'Line frequency',
    'raritan_sensors_temperature_in_degree_celsius': 'Measured temperature',
    'raritan_sensors_humidity_in_percent': 'Measured humidity',
    'raritan_sensors_absolute_humidity_in_g_per_cubic_meter':
        'Measured absolute humidity'}
