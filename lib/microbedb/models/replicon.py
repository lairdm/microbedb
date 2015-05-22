import os
from . import Base, fetch_session
from .version import Version
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import make_transient
from sqlalchemy import exc as sqlalcexcept
import microbedb.config_singleton
import pprint

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
    protein_num = Column(Integer)
    rep_size = Column(Integer)
    rna_num = Column(Integer)
    file_types = Column(Text)
