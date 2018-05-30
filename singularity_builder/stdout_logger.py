""" Sets up a logger with stdout as target"""

import logging
import sys

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
LOGGER.addHandler(HANDLER)
