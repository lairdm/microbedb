'''
Library to fetch and process directories from ncbi

Controls the process of fetching the index from NCBI,
parse and either download a new version of a genome
or clone the previous version depending on if the 
checksums have changed.
'''

import ftplib
import gzip
import logging
from Bio import SeqIO
import os.path
from urlparse import urlparse
import microbedb.config_singleton
from .models import *
import pprint

class ncbi_fetcher():

    def __init__(self):

        self.cfg = microbedb.config_singleton.getConfig()
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initializing ncbi_fetcher")

        self.logger.debug("Connecting to ncbi's ftp: {}".format(self.cfg.ncbi_ftp))
        self.ftp = ftplib.FTP(self.cfg.ncbi_ftp)
        self.ftp.login()
        self.ftp.cwd(self.cfg.ncbi_rootdir)

    def __str__(self):
        return "ncbi_fetcher()"

    '''
    Fetch the root directory of NCBI's prokaryotic
    genomes, for each send it for processing all the
    isolates within.
    '''
    def sync_version(self):

        # First we fetch all the files
        files = self.ftp.nlst()

        for file in files:
            self.logger.info("Processing remote directory: {}".format(file))
            self.process_remote_directory(file)

            
    '''
    For a given species directory in NCBI's ftp
    directory, download the assembly summary file,
    and send it down the line for processing
    '''
    def process_remote_directory(self, genomedir):
        
        assembly_lines = []
        self.logger.debug("Processing genome directory {}".format(genomedir))

        try:
            self.logger.debug("Fetching genome summary file {}/assembly_summary.txt".format(genomedir))
            self.ftp.retrlines("RETR {}/assembly_summary.txt".format(genomedir), assembly_lines.append)

            for line in assembly_lines:
                self.logger.debug("Summary file line: {}".format(line))
                self.process_summary(genomedir, line)

        except ftplib.error_perm as e:
            self.logger.exception("Perm FTP error: " + str(e))
        except Exception as e:
            self.logger.exception("Unknown exception: " + str(e))


    #
    # For a given line of a summary file, determine
    # if we should process it. Is it a complete 
    # genome?
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

        self.logger.info("Found complete genome: " + str(assembly))

        self.process_genome(genomedir,
                            assembly)

    #
    # We have a genome we know is complete,
    # process it.
    #
    def process_genome(self, current_genome, assembly):
        self.logger.info("Processing genome: {}, assembly_accession: {}, asm_name: {}".format(current_genome, assembly['assembly_accession'], assembly['asm_name']))

        # Fetch the summary file with the checksums
        if not assembly['ftp_path']:
            self.logger.error("No FTP path for genome {}/{}".format(current_genome, assembly['assembly_accession']))
            return

        # Build the url for the checksum file, then grab it
        url_pieces = urlparse(assembly['ftp_path'])
        summary_url = "{}/md5checksums.txt".format(url_pieces.path)
        checksums = []
        self.logger.debug("RETR checksum file {}".format(summary_url))
        self.ftp.retrlines("RETR {}".format(summary_url), checksums.append)

        # See if we have this genome in the current version of the
        # database already
        gp = GenomeProject.find(**assembly)

        # If we didn't find the GP, then consider it changed already
        genome_changed = True if not gp else False
        self.logger.debug("Starting checksum check, genome has changed: {}".format(genome_changed))

        # Go through the checksum lines, and for each see if we have
        # that checksum already and if it matches the current microbedb version
        for line in checksums:
            self.logger.debug("Examining checksum file line: {}".format(line))
            filename, md5 = self.separate_md5line(line)

            # If the checksum if different (or wasn't found) we know the genome
            # has changed and we'll have tp update it
            if not GenomeProject_Checksum.verify(filename, md5):
                self.logger.debug("Checksum for file {} has changed".format(filename))
                genome_changed = True

        # If the genome has changed we're going to have to download and process it
        if genome_changed:
            self.logger.info("Genome {}/{} has changed, creating a new copy".format(assembly['assembly_accession'], assembly['asm_name']))
            # Start fresh, don't reuse the previous GP, even if found
            # We're going to maintain the same directory structure, so we need the directory
            # name for the species
            assembly['genome_name'] = current_genome
            gp = GenomeProject.create_gp(version='latest', **assembly)

            # Uh-oh, we had a problem making the new GenomeProject, bail
            if not gp:
                self.logger.error("We had a problem making the GenomeProject {}/{}".format(current_genome, assembly['assembly_accession']))
                return

            # Fetch metadata from source or clone it from current version if we have
            # it, here

            # And ensure we have all the taxonomy information for this genome
            if gp.taxid:
                Taxonomy.find_or_create(gp.taxid)

            if gp.species_taxid:
                Taxonomy.find_or_create(gp.species_taxid)

            # Go fetch the genome files from NCBI
            self.fetch_genome(gp, url_pieces.path, checksums)

            # Now that we should have the files, process and load
            # the replicons
            self.logger.info("Parsing genbank file for gp {}".format(gp.gpv_id))
            self.parse_replicons(gp)

            try:
                # Go find all the file extensions in
                # the directory structure and record them
                exts = GenomeProject.find_extensions(gp.gpv_id, gp=gp)
                if exts:
                    gp.file_types = ' '.join(exts)
                    self.logger.debug("Commiting extensions for gpv_id {}: {}".format(gp.gpv_id, gp.file_types))
                    gp.commit()

            except Exception as e:
                self.logger.exception("Error fetching file types for gpv_id {}".format(gp.gpv_id))
                
        # Nothing changed in this genome so just clone everything and
        # make the needed symlinks
        else:
            self.logger.info("Genome {}/{} hasn't changed, cloning".format(assembly['assembly_accession'], assembly['asm_name']))

            # What if the script was restarted? And we've already loaded this genone?
            # Do nothing then
            if gp.version_id == Version.latest():
                self.logger.error("We already seem to have gpv_id {} for version {}, skipping".format(gp.gpv_id, gp.version_id))
                return

            # Copy the genome and all realted pieces
            self.copy_genome(gp)

    #
    # The genome project hasn't changed, therefore we need to copy
    # the entries to the new version and symlink the old files
    #
    # We'll clone the GP, and in that routine the Replicons should
    # automatically get cloned as well
    #
    def copy_genome(self, gp):
        self.logger.info("Copying GenomeProject {}".format(gp.gpv_id))
        gp.clone_gp()

        self.logger.debug("New gpv_id: {}".format(gp.gpv_id))

    #
    # We have an updated genome, grab the files,
    # and parse them
    #
    def fetch_genome(self, gp, ftp_path, checksums):
        session = fetch_session()
        self.logger.debug("Fetching genome {} from {}".format(gp.gpv_id, ftp_path))

        if not os.path.exists(gp.gpv_directory):
            self.logger.info("making directory {}".format(gp.gpv_directory))
            os.makedirs(gp.gpv_directory)
            
        for line in checksums:
            filename, md5 = self.separate_md5line(line)

            try:
                # Retreive the genome file from ncbi
                local_filename = os.path.join(gp.gpv_directory, filename)
                self.logger.debug("Using local filename {}".format(local_filename))
                self.ftp.retrbinary("RETR {}/{}".format(ftp_path, filename),
                                    open(local_filename,'wb').write)

                # Insert the checksum
                gpcs = GenomeProject_Checksum(filename=filename, 
                                              checksum=md5, 
                                              version=Version.fetch("latest"),
                                              gpv_id=gp.gpv_id)

                session.add(gpcs)
                session.commit()

                # Unzip the file
                with gzip.open(local_filename, 'rb') as infile:
                    with open(local_filename[:-3], 'w') as outfile:
                        for line in infile:
                            outfile.write(line)
                
                # Remove the gzip files
                if os.path.exists(local_filename):
                    os.unlink(local_filename)

            except Exception as e:
                self.logger.exception("Exception inserting checksum for {}: ".format(filename))
                session.rollback()
                raise e


    def parse_replicons(self, gp):

        try:
            session = fetch_session()

            genbank_file = "{}/{}_{}_genomic.gbff".format(gp.gpv_directory, gp.assembly_accession, gp.asm_name)
            self.logger.debug("Using genbank file {}".format(genbank_file))

            if not os.path.exists(genbank_file):
                raise Exception("Genbank file for {}_{} (gpv_id {}) doesn't exist".format(gp.assembly_accession, gp.asm_name, gp.gpv_id))

            type_count = {'chromosome_num': 0,
                          'plasmid_num': 0,
                          'contig_num': 0 }

            # Parse the genbank file and for each replicon in it
            # parse and load it
            with open(genbank_file, 'rU') as infile:
                for record in SeqIO.parse(infile, "genbank"):
                    rep = Replicon.create_from_genbank(gp, record)
                    type_count[rep.rep_type+"_num"] += 1

            self.logger.debug("Updating GP with rep_types: " + str(type_count))

            # Try to find the gram stain
            gram = Taxonomy.guess_gram(gp.species_taxid)
            if gram:
                type_count['gram_stain'] = gram

            GenomeProject_Meta.create_or_update(gp.gpv_id, **type_count)

            # Commit the rep_type changes
            session.commit()

        except Exception as e:
            self.logger.exception("Error updating GP with rep_type counts: " + str(e))
            session.rollback()
            raise e

    '''
    The mappings of an ncbi assembly summary file to fields we need
    '''
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
