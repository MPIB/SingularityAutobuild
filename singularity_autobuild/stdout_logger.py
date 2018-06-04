""" Sets up a shared logger with stdout as target.

Informative logging is done with GitLabs ci pipeline in mind.
Logging not expected to cause long output is logged to stdout to
show up inside a pipelines job log.
"""

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
