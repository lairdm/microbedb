#!/usr/bin/env python

import sys, argparse, os
MYPATH = os.path.abspath(os.path.dirname(__file__))
PARENTPATH = os.path.abspath(os.path.dirname(MYPATH))
LIBPATH = os.path.join(PARENTPATH, 'lib')
sys.path.append(LIBPATH)
import microbedb.config_singleton
import microbedb.db_singleton
from microbedb.ncbi import ncbi_fetcher
import pprint

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Test the FTP connection to NCBI')
    parser.add_argument('-c','--config', dest='config', help='Config file', required=True)

    opts = parser.parse_args()

    cfg = microbedb.config_singleton.initConfig(opts.config)
    conn = microbedb.db_singleton.initDB()

    fetcher = ncbi_fetcher('/mypath')

    fetcher.sync_version()
