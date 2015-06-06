#!/usr/bin/env python

'''
Query NCBI and update MicrobeDB.

Unless the -n option is given a new version of microbedb
will be created and populated.

'''

import sys, argparse, os, logging

# Setup lib paths
PARENTPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(PARENTPATH, 'lib'))
import microbedb.config_singleton
from microbedb.logger_singleton import initLogger
from microbedb.models import *
from microbedb.ncbi import ncbi_fetcher

def main():
    parser = argParser()
    opts = parser.parse_args()
    
    cfg = microbedb.config_singleton.initConfig(opts.config)

    initLogger(default_path=cfg.logger_cfg)
    logger = logging.getLogger(__name__)

    logger.info("Initializing MicrobeDB update")

    if opts.noversion:
        version = Version.latest()
    else:
        version = Version.get_next()
        version = version.version_id

    logger.info("Updating MicrobeDB version {}".format(version))

    fetcher = ncbi_fetcher()

    fetcher.sync_version()

    # We're done so set the current microbedb version to the new current one
    Version.set_current(version)

def argParser():

    parser = argparse.ArgumentParser(description='Update MicrobeDB from NCBI\'s ftp site')
    parser.add_argument('-c','--config', dest='config', help='Config file', required=True)
    parser.add_argument('-n','--noversion', action='store_true', default=False, dest='noversion', help='Don\'t create a new version, use the latest', required=False)

    return parser

if __name__ == "__main__":

    main()

