#!/usr/bin/env python

import sys, argparse, os
PARENTPATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.join(PARENTPATH, 'lib'))
import microbedb.config_singleton
import microbedb.db_singleton
from microbedb.models import *
#from microbedb.models import init_mapper
#from microbedb.dbmapper import GenomeProject, GenomeProject_Meta, GenomeProject_Checksum, Version, init_mapper
import pprint

def main():
    parser = argParser()
    opts = parser.parse_args()

    cfg = microbedb.config_singleton.initConfig(opts.config)

    session = fetch_session()

    gp = GenomeProject(assembly_accession='ABCDE', asm_name='Z123')

#    session.add(gp)
#    session.commit()
#    print Version.latest()

    v = Version.get_next()
    print v.version_id
    print v.dl_directory
    print v.version_date

def argParser():

    parser = argparse.ArgumentParser(description='Test the SQL Alchemy mapper')
    parser.add_argument('-c','--config', dest='config', help='Config file', required=True)

    return parser

if __name__ == "__main__":

    main()
