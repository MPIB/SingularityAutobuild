""" Sets up a shared logger



Informative logging, with stdout as target, is done with GitLabs ci pipeline in mind.
Logging not expected to cause long output is logged to stdout to
show up inside a pipelines job log.
"""

import logging
import sys

def get_stdout_logger() -> logging.Logger:
    """ Sets up logger with a stream handler for stdout.

    :returns: A logging.Logger Object with  a handler set
              up to log to stdout.
    """
    _logger = logging.getLogger()
    _logger.setLevel(logging.DEBUG)

    _handler = logging.StreamHandler(sys.stdout)
    _handler.setLevel(logging.DEBUG)
    _handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
    _logger.addHandler(_handler)
    return _logger
