'''
Replicon model

Represents an individual relicon (chromosome, plasmid, contig)
associated with a GenomeProject.
'''

import os
import re
import logging
from . import Base, fetch_session
from .version import Version
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import make_transient
from sqlalchemy import exc as sqlalcexcept
import microbedb.config_singleton
import pprint

logger = logging.getLogger(__name__)

class Replicon(Base):
    __tablename__ = 'replicon'
    rpv_id = Column(Integer, primary_key=True)
    gpv_id = Column(Integer)
    version_id = Column(Integer)
    rep_accnum = Column(String(14), nullable=False)
    definition = Column(Text)
    rep_type = Column(Enum('chromosome', 'plasmid', 'contig'))
    rep_ginum = Column(String(24))
    file_name = Column(Text)
    cds_num = Column(Integer)
    gene_num = Column(Integer)
    rep_size = Column(Integer)
    rna_num = Column(Integer)

    def __str__(self):
        return "Replicon(): rpv_id: {}, gpv_id {}, version: {}".format(self.rpv_id, self.gpv_id, self.version_id)

    @classmethod
    def create_from_genbank(cls, gp, record, version='latest'):
        global logger
        logger.info("Creating Replicon from genbank record, gpv_id: {}, version: {}".format(gp.gpv_id, version))

        session = fetch_session()

        try:
            logger.debug("Creating Replicon, gpv_id: {}, accnum: {}, assembly_accession: {}".format(gp.gpv_id, record.id, gp.assembly_accession))
            rep = Replicon(gpv_id=gp.gpv_id,
                           version_id=Version.fetch(version),
                           rep_accnum=record.id,
                           definition=record.description,
                           file_name = "{}_{}".format(gp.assembly_accession, gp.asm_name))

            if 'gi' in record.annotations:
                rep.rep_ginum = record.annotations['gi']
            
            # We need to find how many cds and gene records now
            CDS = 0
            gene = 0
            rna = 0
            rna_pat = re.compile('RNA')
            for feat in record.features:
                if feat.type == 'CDS':
                    CDS += 1
                elif feat.type == 'gene':
                    gene += 1
                elif rna_pat.match(feat.type):
                    rna += 1

            rep.cds_num = CDS
            rep.gene_num = gene
            rep.rna_num = rna
            rep.rep_size = len(record.seq)
            logger.debug("Replicon features, genes: {}, CDS: {}, RNA: {}, size: {}".format(gene, CDS, rna, rep.rep_size))

            rep.rep_type = find_replicon_type(record.description)
            logger.debug("We think this replicon is of type {}".format(rep.rep_type))

            session.add(rep)
            session.commit()

            return rep

        except sqlalcexcept.IntegrityError as e:
            logger.exception("Error inserting Replicon: " + str(e))
            session.rollback()
            return None

        except Exception as e:
            logger.exception("Unknown exception creating Replicon: " + str(e))
            return None

    '''
    Copy a Replicon, creating a new Replicon object that is returned.

    If any properties are given in kwargs, update the newly created
    object with these values rather than from the original object.
    '''
    def copy_and_update(self, **kwargs):
        global logger
        logger.info("Copy and update replicon {}".format(self.rpv_id))

        session = fetch_session()

        # Special case since version can be passed in as a string
        # such as 'latest' or 'current'
        if 'version_id' in kwargs:
            kwargs['version_id'] = Version.fetch(kwargs['version_id'])
        elif 'version' in kwargs:
            kwargs['version_id'] = Version.fetch(kwargs['version'])

        try:
            # Create a Replicon object and begin copying fields
            rep = Replicon()

            for col in Replicon.__table__.columns:
                prop = rep.__mapper__._columntoproperty[col].key
                # rpv_id is autoinc, don't copy that!
                if prop == 'rpv_id':
                    continue
                elif prop in kwargs:
                    setattr(rep, prop, kwargs[prop])
                elif getattr(self, prop):
                    setattr(rep, prop, getattr(self, prop))
                    
            logger.debug("Committing Replicon: " + str(rep))
            session.add(rep)
            session.commit()

            return rep

        except sqlalcexcept.IntegrityError as e:
            logger.exception("Replicon insertion error (IntegrityError): " + str(e))
            session.rollback()
            return None
        except Exception as e:
            logger.exception("Unknown error creating Replicon: " + str(e))
            return None


    '''
    Remove the replicon from the database
    '''
    @classmethod
    def remove_replicon(cls, rpv_id):
        global logger
        logger.info("Removing replicon rpv_id {}".format(rpv_id))

        session = fetch_session()

        try:
            rep = session.query(Replicon).filter(Replicon.rpv_id == rpv_id).first()

            if not rep:
                logger.error("Replicon rpv_id {} not found".format(rpv_id))
                raise Exception("Replicon not found")

            session.delete(rep)
            session.commit()

        except Exception as e:
            logger.exception("Error removing replicon rpv_id {}".format(rpv_id))
            session.rollback()
            raise e

                    

#
# Test the genome description line to see if it's a complete
# genome, plasmid or contig
# 
# We're going to be a little strict, if we can't figure out what
# it is, we're going to say contig
#
def find_replicon_type(desc):
    global logger
    logger.debug("Testing description for genome type: {}".format(desc))

    # Convert to lower case
    desc = desc.lower()

    if re.search('plasmid', desc):
        return 'plasmid'
    elif re.search('complete genome', desc):
        return 'chromosome'
    elif re.search('complete sequence', desc):
        return 'chromosome'
    elif re.search('chromosome', desc):
        return 'chromosome'

    return 'contig'
