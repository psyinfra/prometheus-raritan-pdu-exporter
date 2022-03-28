import urllib3
import logging

DEFAULT_PORT = 9840

# Raritan PDU has no SSL certificate, ignore the ensuing warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# External (root level) logging level
logging.basicConfig(
    level=logging.WARNING, format='[%(asctime)s] %(levelname)s: %(message)s')

__all__ = [DEFAULT_PORT]
