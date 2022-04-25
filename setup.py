from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="prometheus-raritan-pdu-exporter",
    version="2.1.0",
    description="Python-based Raritan PDU exporter for prometheus.io",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/psyinfra/prometheus-raritan-pdu-exporter",
    author="Niels Reuter",
    author_email="n.reuter@fz-juelich.de",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: System :: Monitoring"
    ],
    keywords="raritan, pdu, monitoring, prometheus",
    packages=find_packages(),
    python_requires=">=3.7, <4",
    install_requires=[
        "prometheus_client~=0.14.0",
        "aiohttp~=3.8.0"],
    project_urls={
        "Bug Reports":
            "https://github.com/psyinfra/prometheus-raritan-pdu-exporter/issues",  # noqa: E501
        "Source":
            "https://github.com/psyinfra/prometheus-raritan-pdu-exporter",
    }
)
