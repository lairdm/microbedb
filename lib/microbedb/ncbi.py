'''
Library to fetch and process directories from ncbi
'''

import ftplib
import os.path
from urlparse import urlparse
import microbedb.config_singleton
from .models import *
import pprint

class ncbi_fetcher():

    def __init__(self, rootdir):

        self.cfg = microbedb.config_singleton.getConfig()

        self.ftp = ftplib.FTP(self.cfg.ncbi_ftp)
        self.ftp.login()
        self.ftp.cwd(self.cfg.ncbi_rootdir)


    def sync_version(self):

        # First we fetch all the files
        files = self.ftp.nlst()

        for file in files:
            print "Processing {}".format(file)

            
        pprint.pprint(files)
#        self.fetch_summary("blah")
        self.process_remote_directory(files[1])
#        ftp.retrlines('LIST')

    def process_remote_directory(self, genomedir):
        
        assembly_lines = []

        try:
            # I'm not thrilled about this, but
            # I can't pass an extra argument to the 
            # retrlines callback
            self.current_genome = genomedir

            self.ftp.retrlines("RETR {}/assembly_summary.txt".format(genomedir), assembly_lines.append)
#            self.ftp.retrlines("RETR {}/assembly_summary.txt".format(genomedir), self.process_summary)

        except ftplib.error_perm as e:
            print "Perm error"
            print e
        except Exception as e:
            print e

        for line in assembly_lines:
            self.process_summary(genomedir, line)

    #
    # For a given line of a summary file, determine
    # if we should process it
    #
    def process_summary(self, genomedir, line):

        # Skip comment lines
        if line.startswith("#"):
            return
        
        # Split the line in to it's fields
        assembly = self.map_summary(line)

        # We're only interested in complete genomes
        if assembly['assembly_level'] != 'Complete Genome':
            return

        pprint.pprint(assembly)
#        print line

        self.process_genome(genomedir,
                            assembly)

    #
    # We have a genome we know is complete,
    # process it.
    #
    def process_genome(self, current_genome, assembly):

        # Fetch the summary file with the checksums
        if not assembly['ftp_path']:
            print "No ftp path for genome {}/{} found!".format(current_genome, assembly['assembly_accession'])
            return

        summary_url = "{}/md5checksums.txt".format(assembly['ftp_path'])
        url_pieces = urlparse(summary_url)
        print url_pieces
        checksums = []
        self.ftp.retrlines("RETR {}".format(url_pieces.path), checksums.append)

        gp = GenomeProject.find(**assembly)

        print gp

        genome_changed = True if not gp else False
        for line in checksums:
            filename, md5 = self.separate_md5line(line)
            print line
            if not GenomeProject_Checksum.verify(filename, md5):
                genome_changed = True
            print "Found: {} : {} : {}".format(filename, md5, genome_changed)

        if genome_changed:
            # Start fresh
            gp = GenomeProject.create_gp(version='latest', **assembly)
            self.update_genome(gp, checksums)
        elif not created:
            # It hasn't changed but a record already
            # seems to exist, we'll skip this for now but
            # we might want to do some checking here in the future
            pass
        else:
            self.copy_genome(gp)

    #
    # The genome project hasn't changed, therefore we need to copy
    # the entries to the new version and symlink the old files
    #
    def copy_genome(self, gp):
        gp.clone_gp()

        print "New gpv_id " + str(gp.gpv_id)

        # We'll need to do something with the replicons and such here

    #
    # We have an updated genome, grab the files,
    # and parse the files
    #
    def update_genome(self, gp, checksums):
        pass

        # Attempt to get the metadata from wherever it come from and
        # insert it here

    def map_summary(self, line):
        pieces = line.split("\t")

        assembly = {
            'assembly_accession': pieces[0],
            'bioproject': pieces[1],
            'biosample': pieces[2],
            'wgs_master': pieces[3],
            'refseq_category_taxid': pieces[4],
            'taxid': pieces[5],
            'species_taxid': pieces[6],
            'org_name': pieces[7],
            'infraspecific_name': pieces[8],
            'isolate': pieces[9],
            'version_status': pieces[10],
            'assembly_level': pieces[11],
            'release_type': pieces[12],
            'genome_rep': pieces[13],
            'release_date': pieces[14],
            'asm_name': pieces[15],
            'submitter': pieces[16],
            'gbrs_paired_asm': pieces[17],
            'paired_asm_comp': pieces[18],
            'ftp_path': pieces[19]
            }

        return assembly

    # Separate an NCBI checksum file line in to pieces
    def separate_md5line(self, line):
        pieces = line.split()

        pathbit, filename = os.path.split(pieces[1])

        return filename, pieces[0]
