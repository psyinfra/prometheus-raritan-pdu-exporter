import logging


class LogLevels(object):
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    DEEP_DEBUG = 5

    all = {
        'critical': CRITICAL,
        'error': ERROR,
        'warning': WARNING,
        'info': INFO,
        'debug': DEBUG,
        'deep-debug': DEEP_DEBUG}


__all__ = [LogLevels]
