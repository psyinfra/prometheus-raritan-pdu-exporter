# Prometheus Raritan PDU Exporter
Python-based Raritan PDU exporter for [prometheus.io](https://prometheus.io/).

This exporter uses the Raritan json-rpc API to find inlet sensors, outlet
sensors, and devices to expose their readings to the Prometheus monitoring
system.

We have purposely opted not to use the Raritan PDU Python API since direct
calls to the json-rpc API are very straight-forward. Furthermore, only a
handful of methods are used (`getInlets`, `getOutlets`, `getMetaData`, 
`getDeviceSlots`, `getDevice`, `getReading` and `getState`) on the `/bulk`
endpoint, ignoring most of the methods included in the Python API. As a result
we do not have to bundle the Raritan PDU Python API with this project.

## Usage for PDU collection

    prometheus_raritan_pdu_exporter.py [-h] -c config [-w listen_address]
                                       [-t] [-k]
        
    optional arguments:
      -h, --help            show this help message and exit
      -c config, --config config
                            configuration json file containing PDU addresses and
                            login info
      -w listen_address, --web.listen-address listen_address
                            Address and port to listen on (default = :9840)
      -t, --threading       whether to use multi-threading for sensor readings
                            (faster)
      -k, --insecure        allow a connection to an insecure raritan API


### Example

    python3 prometheus_raritan_pdu_exporter.py --web.listen-address :9840 -t -k


## Installation

    git clone git@jugit.fz-juelich.de:inm7/infrastructure/prometheus_raritan_pdu_exporter.git
    cd prometheus_raritan_pdu_exporter
    pip install -r requirements.txt

