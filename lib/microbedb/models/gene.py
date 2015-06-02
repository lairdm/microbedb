import os
from . import Base, fetch_session
from .version import Version
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import make_transient
from sqlalchemy import exc as sqlalcexcept
import microbedb.config_singleton
import pprint

#
# We're likely not going to use this model, we'll go
# straight to the flat files if needed
#

class Gene(Base):
    __tablename__ = 'gene'
    gene_id = Column(Integer, primary_key=True)
    rpv_id = Column(Integer)
    version_id = Column(Integer)
    gpv_id = Column(Integer)
    gid = Column(Integer)
    pid = Column(Integer)
    protein_accnum = Column(String(12))
    gene_type = Column(Enum('CDS', 'tRNA', 'rRNA', 'ncRNA', 'misc_RNA'))
    gene_start = Column(Integer)
    gene_end = Column(Integer)
    gene_length = Column(Integer)
    gene_strand = Column(Enum('+', '-', '1', '-1', '0'))
    gene_name = Column(String(50))
    locus_tag = Column(String(50))
    gene_product = Column(Text)
