import os
import sys
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.sql.expression import desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from sqlalchemy import create_engine
import microbedb.config_singleton

Base = declarative_base()

class GenomeProject(Base):
    __tablename__ = 'genomeproject'
    gpv_id = Column(Integer, primary_key=True)
    assembly_accession = Column(String(16), nullable=False)
    asm_name = Column(String(12), nullable=False)
    version_id = Column(Integer, default=0)
    bioproject = Column(String(14))
    biosample = Column(String(14))
    taxon_id = Column(Integer)
    org_name = Column(Text)
    infraspecific_name = Column(String(24))
    submitter = Column(Text)
    release_date = Column(Date)
    gpv_directory = Column(Text)

class GenomeProject_Meta(Base):
    __tablename__ = 'genomeproject_meta'
    gpv_id = Column(Integer, primary_key=True)
    gram_stain = Column(Enum('+', '-', 'neither', 'unknown'), default='unknown')
    genome_gc = Column(Float(precision='4.2'), default=0.00)
    patho_status = Column(Enum('pathogen', 'nonpathogen', 'unknown'), default='unknown')
    disease = Column(Text)
    genome_size = Column(Float(precision='4.2'), default=0.00)
    pathogenic_in = Column(Text)
    temp_range = Column(Enum('unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic'), default='unknown')
    habitat = Column(Enum('unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic'), default='unknown')
    shape = Column(Text)
    arrangement = Column(Text)
    endospore = Column(Enum('yes', 'no', 'unknown'), default='unknown')
    motility = Column(Enum('yes', 'no', 'unknown'), default='unknown')
    salinity = Column(Text)
    oxygen_req = Column(Enum('unknown', 'aerobic', 'microaerophilic', 'facultative', 'anaerobic'), default='unknown')
    chromosome_num = Column(Integer, default=0)
    plasmic_num = Column(Integer, default=0)
    contig_num = Column(Integer, default=0)

class GenomeProject_Checksum(Base):
    __tablename__ = 'genomeproject_checksum'
    gpv_id = Column(Integer, primary_key=True)
    file = Column(String(24))
    checksum = Column(String(32))

class Version(Base):
    __tablename__ = 'version'
    version_id = Column(Integer, primary_key=True)
    dl_directory = Column(Text)
    version_date = Column(Date, default=func.now())
    used_by = Column(Text)
    is_current = Column(Boolean, default=False)

    @classmethod
    def latest(cls):
        global session
        try:
            return session.query(Version).order_by(desc(Version.version_id)).first().version_id
        except:
            return None

    @classmethod
    def current(cls):
        global session
        try:
            return session.query(Version).filter(is_current=True).first().version_id
        except:
            return None

    @classmethod
    def get_next(cls):
        global session

        cfg = microbedb.config_singleton.getConfig()

        v = Version()
        session.add(v)
        session.commit()

        v.dl_directory = os.path.join(cfg.basedir, str(v.version_id))
        session.commit()

        return v

session = None

def init_mapper():
    global session
    global Base

    # We're going to follow the singleton pattern
    if session:
        return session

    cfg = microbedb.config_singleton.getConfig()

    engine = create_engine('mysql://{}:{}@{}/{}?charset=utf8&use_unicode=0'.format(cfg.db_user, cfg.db_password, cfg.db_host, cfg.database), pool_recycle=3600)

    Base.metadata.bind = engine

    DBSession = sessionmaker(bind=engine)

    session = DBSession()

    return session

