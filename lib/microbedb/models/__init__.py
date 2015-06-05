from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import microbedb.config_singleton

Base = declarative_base()
session = None

def fetch_session():
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

from genomeproject import GenomeProject, GenomeProject_Meta, GenomeProject_Checksum
from replicon import Replicon
from version import Version
from taxonomy import Taxonomy

__all__ = ['GenomeProject', 'GenomeProject_Meta', 'GenomeProject_Checksum',
           'Replicon',
           'Version',
           'Taxonomy',
           'fetch_session'
    ]

