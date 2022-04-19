# CHange Log

## v2.0.0

Released on April 19th, 2022

### Added
  * Expand logging for debug mode
  * Add `aiohttp` and `asyncio` dependencies for asynchronous JSON-RPC requests
  * Custom JSON-RPC handlers for the Raritan PDU's interpretation of the standard
  * Dataclass interfaces for Raritan objects (e.g., connectors, sensors, poles, etc.)
    * Interfaces are frozen to prevent runtime modification

### Changed
  * Replace threading with async for PDU sensor setup
  * Replace threading with async for PDU sensor reading
  * Fix overlapping requests clearing sensor data
  * Specify SSL verification in config file
    * False skips verification
    * True uses default verification
    * A string filepath of a SHA256 digest
  * Refactor code for brevity and clarity
  * Separate bulk request steps into multiple methods for easier debugging
  * Adjust existing tests to match refactoring

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
