# Change Log

## v2.1.0

Released on April 25th, 2022

### Breaking Changes
  * Change metric naming to raritanpdu_<metric>_<unit>{_total} where metric and unit words are no longer separated by underscores

### Changes
  * Adjust tests to match new naming scheme
  * Add `_total` to counter metric names


## v2.0.1

Released on April 21st, 2022

### Added
  * Testing with tox using `tox.ini`
  * Add `pyproject.toml`, `setup.cfg`, and `setup.py` for easier packaging
  * Add `ssl` field to `config.json-example`

### Changed
  * Avoid event loops in Exporter setup and read methods to address asyncio `DeprecationWarning` in py310
  * Change minimum Python version in badges from 3.6+ to 3.7+
  * Update installation instructions in `README.md`
  * Update usage instructions in `README.md`
  * Update testing instructions in `README.md`
  * Expand `.gitignore`
  * Change `LICENSE` to `LICENSE.txt`
  * Adjust github tests workflow to use tox

### Removed
  * `requirements.txt` and `test-requirements.txt` in favor of `setup.py` and `tox.ini`

## v2.0.0

Released on April 19th, 2022

### Breaking Changes
  * Move SSL verification from argument to configuration file, allowing SSL verification to be PDU specific
    * Remove `--insecure` from arguments
    * Add `ssl` key to PDU configuration file
      * `False` skips verification
      * `True` uses default verification
  * Change metric naming scheme from `raritan_sensors_<metric>_in_<unit>` to `raritan_pdu_<metric>_<unit>`
  * Change default listen port from `9840` to `9950` to match the [allocated default port](https://github.com/prometheus/prometheus/wiki/Default-port-allocations) for the Raritan PDU Exporter

### Added
  * Expand logging for debug mode
  * Add `aiohttp` dependency for asynchronous JSON-RPC requests
  * Custom JSON-RPC handlers for the Raritan PDU's interpretation of the standard
  * Dataclass interfaces for Raritan objects (e.g., connectors, sensors, poles, etc.)
    * Interfaces are frozen to prevent runtime modification

### Changed
  * Bug fix: concurrent requests to the exporter will no longer conflict and result in truncated responses
  * Bug fix: all responses should now always include all sensors; sensors with a value of 0.0 are no longer omitted from responses
  * Bug fix: sensors with deleted custom labels now use their default identifiers rather than `''`
  * Replace threading with async for PDU sensor setup and readings
  * Refactor code for brevity and clarity
  * Separate bulk request steps into multiple methods for easier debugging
  * Adjust existing tests to match refactoring
  * Change argument `-l`, `--log-level` to allow a list of 2 inputs to specify internal and external log levels, respectively
    * new default is `warning,critical`
    * internal log level concerns logs only from the Raritan PDU Exporter code
    * external log level concerns logs from external modules, such as `aiohttp`

### Removed
  * `jsonrpcclient` and `requests` module dependencies


## v1.0.6

Released on March 30th, 2022

### Added
  * Extend debugging
    * more general information moved to `info` level
    * debugging is more verbose (especially when things go wrong)
  * Add testing using `vcrpy` to record PDU API responses
  * Add CLI argument `-l`, `--log-level` to specify logging level
    * default level is `warning`
    * allowed levels are `critical`, `error`, `warning`, `info`, `debug`
    * note that the `critical` level is unused

### Changed
  * Sensor readings returning `0.0` are no longer marked as null responses
  * Connectors with cleared custom labels now default to their respective IDs rather than `''`


## v1.0.5

Released on July 28th, 2021

### Changed
  * Enable threading by default if more than 1 PDU is in the config file


## v1.0.0

Released on June 24th, 2021

### Added
  * First version of the Prometheus Raritan PDU Exporter
