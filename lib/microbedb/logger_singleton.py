import logging
import os
import json
import logging.config

'''
Module for initializing the logger from a config file, acts
like a singleton


@author: Matthew Laird
@created: May 23, 2015
'''

logger = None

def initLogger(default_path='logging.json', 
               default_level=logging.INFO,
               env_key='LOG_CFG'
           ):
    """
    Setup logging configuration
    """
    global logger

    if logger:
        return logger

    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level, disable_existing_loggers=False)

    logger = logging.getLogger(__name__)

    logger.info("Logging initialized")

    return logger
