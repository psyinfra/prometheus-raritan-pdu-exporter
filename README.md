![Maintainer](https://img.shields.io/badge/maintainer-nhjjr-blue)
![GitHub](https://img.shields.io/github/license/psyinfra/prometheus-raritan-pdu-exporter)
![Build Status](https://github.com/psyinfra/prometheus-raritan-pdu-exporter/actions/workflows/tests.yml/badge.svg)
![GitHub tag (latest by date)](https://img.shields.io/github/v/tag/psyinfra/prometheus-raritan-pdu-exporter?label=version)
![Python Version](https://img.shields.io/badge/python-v3.7+-blue)

# Prometheus Raritan PDU Exporter
Python-based Raritan PDU exporter for [prometheus.io](https://prometheus.io/).

This exporter uses the Raritan JSON-RPC API to find inlet, outlet, pole, and 
device sensors to expose their readings to the Prometheus monitoring system.

We have purposely opted not to use the Raritan PDU Python API since direct
calls to the JSON-RPC API are very straight-forward. Furthermore, only a
handful of methods are used (`getInlets`, `getOutlets`, `getMetaData`, 
`getDeviceSlots`, `getDevice`, `getReading` and `getState`) on the `/bulk`
endpoint, ignoring most of the methods included in the Python API. As a result
we do not have to bundle the Raritan PDU Python API with this project. 

## Installation
```commandline
git clone git@github.com:psyinfra/prometheus-raritan-pdu-exporter.git
cd prometheus_raritan_pdu_exporter
pip install .
```

## Usage for PDU collection

    raritanpdu [-h] -c config [-w LISTEN_ADDRESS] [-l LOG_LEVEL [LOG_LEVEL ...]]

    optional arguments:
      -h, --help            show this help message and exit
      -c config, --config config
                            configuration json file containing PDU addresses 
                            and login info
      -w LISTEN_ADDRESS, --web.listen-address LISTEN_ADDRESS
                            Address and port to listen on (default = :9950)
      -l LOG_LEVEL [LOG_LEVEL ...], --log LOG_LEVEL [LOG_LEVEL ...]
                            Specify logging level for internal and external 
                            logging, respectively (Default is WARNING,CRITICAL)

### Example

```commandline
raritanpdu --web.listen-address :9950
```

The entry points `raritanpdu` and `prometheus_raritan_pdu_exporter` are 
identical and can be used interchangeably.

### Health checks

For every HTTP endpoint other than `/healthcheck`, a collection of metrics from
all of the PDUs in the configuration file will be performed and Prometheus
style metrics will be returned.

The `/healthcheck` endpoint will skip a collection of metrics from the PDUs and
instead immediately return a 200 response with the text "Server is running".
This `/healthcheck` endpoint can be useful when running in Kubernetes or other
platforms to provide a healthcheck that the HTTP server is still successfully
running and isn't hanging.

### Debugging
To enable debugging, set `-l debug` to log debug messages. Note that this will 
provide a lot of additional information and is therefore not a recommended 
setting for long-term use in production.

### Docker Image

A Docker image can be built with:

```commandline
docker build -t raritanpdu .
```

To run the image, expose port 9950 and mount the configuration file:

```commandline
docker run -p 9950:9950 -v <path/to/config.json>:/prometheus-raritan-pdu-exporter/config.json raritanpdu
```

## Testing
Run tests using `tox`

```commandline
pip3 install tox
tox
```

### Testing without VCR cassettes
Our tests use `vcrpy` to record responses from the Raritan PDU JSON-RPC API, 
because access to this data is not guaranteed. If you want to test the 
Raritan PDU Exporter on your PDU setup, copy your `config.json` file to 
`tests/fixtures/config.json` and remove the `tests/fixtures/vcr_cassettes/` 
folder and its contents. Tests can then be run as usual, but will take 
longer as PDUs are requested for data to re-establish the VCR cassettes with 
data from the PDUs in the config file.
