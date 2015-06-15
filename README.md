MicrobeDB v2
==

ABOUT
=====

MicrobeDB provides centralize local storage and access to completed archaeal and bacterial genomes, it's based on [MicrobeDB](https://github.com/mlangill/MicrobeDB) originally written by Morgan Langille.

MicrobeDB v2 is a slimmed down version of the original without the API to access the data, though there are a series of Python SQL Alchemy based classes that can be used to query the data if desired.

What MicrobeDB v2 still does provide is a local mirror of NCBI's set of completed genomes, based on the new directory structure released in 2014.  It provides versioning of mirror sets, and attempts to reduce disk usage by using the md5 checksums provided by NCBI to only download a new version of a genome if it has changed between runs of the MicrobeDB update script.  If a genome has not changed a symlink will be used to point to the first download of a particular genome version.

In addition, per replicon, a gbk, faa and ffn file are generated, named with the refseq accession for that replicon.

REQUIREMENTS
============

* MySQL
* Python

* Python modules (available from pip)
  * MySQL-python
  * SQLAlchemy
  * argparse
  * biopython
  * config
  * requests

* ~20GB of hard drive space per mirror/version of the NCBI dataset.

Installation
============

* Clone the github or download the tarball/zip file from the github home page and unzip it where you wish to install MicrobeDB
* Create your microbedb.config file under the etc/ directory in the installation, a sample can be found under docs/
* Create the database and load the schema found under docs/schema.sql
* Create the microbedb database user and place the credentials in the microbedb.config file

Creating a MicrobeDB version
============================

* In the installation directory run the command:

    bin/update_microbedb.py -c etc/microbedb.config

* If an update session is interrupted it can be rerun with:

    bin/update_microbedb.py -c etc/microbedb.config -n

* To delete a version of MicrobeDB:

    bin/delete_version -c etc/microbedb.config -m <version id> [--removefiles] [-v]

Where the --removefiles option will remove the flat files downloaded from NCBI and -v will offer more verbose output

Logging
=======

There's a logging.json file under etc/ that is used by default for logging updates, this can be customized as desired to change logging level and location.  The default Python logging library and syntax is used.

Overview of MicrobeDB
=====================

* The flat files mirror the NCBI ftp structure and are placed where you specify in the microbedb.config file.

* NCBI now issues multi-record files, meaning all replicons (chromosomes, plasmids, contigs) are included in the same Genbank and Fasta files as separate records, it's up to the user to separate these as needed

* For example a directory structure might look like:

  * Bacteria_2015-06-06
    * Acaryochloris_marina
    * Acetobacterium_woodii
    * Acetobacter_pasteurianus
    * Acetohalobium_arabaticum
      * GCF_000144695.1_ASM14469v1
      	* GCF_000144695.1_ASM14469v1_genomic.fna
	* GCF_000144695.1_ASM14469v1_genomic.gbff
	* GCF_000144695.1_ASM14469v1_genomic.gff
	* GCF_000144695.1_ASM14469v1_protein.faa
	* GCF_000144695.1_ASM14469v1_protein.gpff

* The MySQL database contains 4 main tables:

  * Version
    
    * Each update from NCBI is given a new version number
    * Each version contains one or more GenomeProjects (genomes)

  * GenomeProject

    * Contains information about the genome project and sequencing information
    * Each GenomeProject contains one or more Replicons

  * GenomeProject_Meta

    * Contains metadata about the GenomeProject such as Gram stain, number of chromosomes, plasmids, etc
    * There is a one to one mapping between a GenomeProject and a GenomeProject_Meta record

  * Replicon

    * Chromosome, plasmids, or contigs (for incomplete genomes)
    * E.g. rep_accnum, definition, rep_type, rep_ginum, cds_num, gene_num, genome_id, rep_size, rna_num

Questions/Comments
==================
* Contact: Matthew Laird
* Email: lairdm@sfu.ca
