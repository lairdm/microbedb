'''
Library to fetch and process directories from ncbi
'''

import ftplib
import gzip
from Bio import SeqIO
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

        url_pieces = urlparse(assembly['ftp_path'])
        print url_pieces
        summary_url = "{}/md5checksums.txt".format(url_pieces.path)
        print summary_url
        checksums = []
        self.ftp.retrlines("RETR {}".format(summary_url), checksums.append)

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

            if not gp:
                raise Exception("We had a prolem making the GenomeProject")

            # Fetch metadate from source or clone it from current version if we have
            # it, here

            self.fetch_genome(gp, url_pieces.path, checksums)

            self.parse_replicons(gp)
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
        # clone them probably

    #
    # We have an updated genome, grab the files,
    # and parse them
    #
    def fetch_genome(self, gp, ftp_path, checksums):
        session = fetch_session()

        if not os.path.exists(gp.gpv_directory):
            print "making directory {}".format(gp.gpv_directory)
            os.makedirs(gp.gpv_directory)
            
        for line in checksums:
            filename, md5 = self.separate_md5line(line)

            try:
                # Retreive the genome file from ncbi
                local_filename = "{}/{}".format(gp.gpv_directory, filename)
                print "Using local filename {}".format(local_filename)
                self.ftp.retrbinary("RETR {}/{}".format(ftp_path, filename),
                                    open(local_filename,'wb').write)

                # Insert the checksum
                gpcs = GenomeProject_Checksum(filename=filename, checksum=md5, version=Version.fetch("latest"))
                session.add(gpcs)
                session.commit()

                # Unzip the file
                with gzip.open(local_filename, 'rb') as infile:
                    with open(local_filename[:-3], 'w') as outfile:
                        for line in infile:
                            outfile.write(line)

                # Parse out replicons here

            except Exception as e:
                print "Exception inserting checksum for {}: ".format(filename) + str(e)
                session.rollback()
                raise e

    def parse_replicons(self, gp):

        genbank_file = "{}/{}_{}_genomic.gbff".format(gp.gpv_directory, gp.assembly_accession, gp.asm_name)

        if not os.path.exists(genbank_file):
            raise "Genbank file for {}_{} (gpv_id {}) doesn't exist".format(gp.assembly_accession, gp.asm_name, gp.gpv_id)
        with open(genbank_file, 'rU') as infile:
            for record in SeqIO.parse(infile, "genbank"):
                print dir(record)
                print record.id
                print record.description

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
