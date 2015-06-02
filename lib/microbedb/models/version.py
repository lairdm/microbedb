import os
import logging
from . import Base, fetch_session
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql import func
import microbedb.config_singleton

logger = logging.getLogger(__name__)

class Version(Base):
    __tablename__ = 'version'
    version_id = Column(Integer, primary_key=True)
    dl_directory = Column(Text)
    version_date = Column(Date, default=func.now())
    used_by = Column(Text)
    is_current = Column(Boolean, default=False)

    @classmethod
    def latest(cls):
        session = fetch_session()
        try:
            return session.query(Version).order_by(desc(Version.version_id)).first().version_id
        except:
            return None

    @classmethod
    def current(cls):
        session = fetch_session()
        try:
            return session.query(Version).filter(Version.is_current == True).first().version_id
        except:
            return None

    '''
    Create a new version of microbedb and return it
    '''
    @classmethod
    def get_next(cls):
        session = fetch_session()

        cfg = microbedb.config_singleton.getConfig()

        v = Version()
        session.add(v)
        session.commit()

        v.dl_directory = os.path.join(cfg.basedir, str(v.version_id))
        session.commit()

        return v

    @classmethod
    def fetch(cls, version):

        if version == 'current':
            version = Version.current()
        elif version == 'latest':
            version = Version.latest()

        return version

    @classmethod
    def fetch_path(cls, version):
        version = cls.fetch(version)

        session = fetch_session()

        try:

            return session.query(Version).filter(Version.version_id == version).first().dl_directory
        except:
            return None

    @classmethod
    def mkpath(cls, version):
        global logger

        path = Version.fetch_path(version)
        logger.debug("Making version {} path {}".format(version, path))

        try:
            if not os.path.exists(path):
                os.makedirs(path)

            return True

        except Exception as e:
            logger.exception("Error creating version path for version {}, path {}:".format(version, path))
            return False
