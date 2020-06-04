# Raritan Exporter
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

## Usage for single PDU collection

    raritan_exporter.py [-h] -a address [-p port] [--user user]
                        [--password password] [-k]

    optional arguments:
      -h, --help            show this help message and exit
      -a address, --address address
                            address of the raritan PDU server
      -p port, --port port  listen to this port
      --user user           raritan API user
      --password password   raritan API password
      -k, --insecure        allow a connection to an insecure raritan API

### Example

    python3 raritan_exporter.py -a https://address.of.pdu -p 8001 --user username --password very_secure_password -k

## Usage for multiple PDU collection
The same can be achieved with running multiple instances of the single PDU
collection exporter, except the multi-exporter exposes all metrics on the same
port.

    raritan_multi_exporter.py [-h] -c config [-p port] [-t] [-k]

    optional arguments:
      -h, --help            show this help message and exit
      -c config, --config config
                            configuration json file containing PDU addresses and
                            login info
      -p port, --port port  listen to this port
      -t, --threading       whether to use multi-threading for sensor readings
                            (faster)
      -k, --insecure        allow a connection to an insecure raritan API


### Example

    python3 raritan_multi_exporter.py -c config.json -p 8001 -t -k

## Installation

    git clone git@jugit.fz-juelich.de/inm7/infrastructure/raritan_exporter.git
    cd raritan_exporter
    pip install -r requirements.txt

