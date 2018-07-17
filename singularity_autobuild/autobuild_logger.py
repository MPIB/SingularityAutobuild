# -*- coding: utf-8 -*-
""" Sets up a shared logger

Informative logging, with stdout as target, is done with GitLabs ci pipeline in mind.
Logging not expected to cause long output is logged to stdout to
show up inside a pipelines job log.
"""

import logging
import sys


def get_stdout_logger(name: str = None, level: str = None) -> logging.Logger:
    """ Sets up logger with a stream handler for stdout.

    :param name:    Name of the logger, to be returned.
    :param level:   Level of the logger to be returned.
    :returns:       A logging.Logger Object with  a handler set
                    up to log to stdout.
    """
    if level == 'INFO':
        _log_level = logging.INFO
    elif level == 'ERROR':
        _log_level = logging.ERROR
    elif level == 'DEBUG':
        _log_level = logging.DEBUG
    else:
        _log_level = logging.CRITICAL


    _logger = logging.getLogger(name=name)
    _logger.setLevel(_log_level)

    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(_log_level)
    _handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s - '
        )
    )
    _logger.addHandler(_handler)
    return _logger
