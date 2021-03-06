#!/usr/bin/env python

import sys, argparse, os, logging

# Setup lib paths
PARENTPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(PARENTPATH, 'lib'))
import microbedb.config_singleton
from microbedb.logger_singleton import initLogger
from microbedb.models import *
from microbedb.ncbi import ncbi_fetcher
from microbedb.prompt import query_yes_no

def main():
    parser = argParser()
    opts = parser.parse_args()

    cfg = microbedb.config_singleton.initConfig(opts.config)

    logger = logging.getLogger(__name__)
    logging_level = logging.DEBUG if opts.verbose else logging.INFO
    logging.basicConfig(level=logging_level, disable_existing_loggers=False)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    print "Removing MicrobeDB GenomeProject gpv_id {}".format(opts.gpv)

    remove_files = opts.removefiles

    if not opts.force:
        confirm = query_yes_no("Remove gpv_id {}?".format(opts.gpv), default=None)

        if not confirm:
            print "Aborting removal"
            return
        
        if remove_files:
            remove_files = query_yes_no("Are you sure you want to remove the flat files?", default="no")

    print "Removing GenomeProject, files too: {}".format(remove_files)

    try:
        GenomeProject.remove_gp(opts.gpv, remove_files=remove_files)

    except Exception as e:
        print "Error removing gpv_id {}: ".format(opts.gpv) + str(e)

def argParser():

    parser = argparse.ArgumentParser(description='Remove a specific GenomeProject')
    parser.add_argument('-c','--config', dest='config', help='Config file', required=True)
    parser.add_argument('-g','--gpvid', dest='gpv', help='The GenomeProject gpv_id to remove', required=True)
    parser.add_argument('--removefiles', action='store_true', default=False, dest='removefiles', help='Remove the flat files associated with the genome project', required=False)
    parser.add_argument('--force', action='store_true', default=False, dest='force', help='Force removal without prompt', required=False)
    parser.add_argument('-v','--verbose', action='store_true', default=False, dest='verbose', help='Verbose output', required=False)

    return parser

if __name__ == "__main__":

    main()
