'''
Version model
(microbedb.models.version)

Represents a version of MicrobeDB that GenomeProjects are
associated with.
'''

import os
import logging
import shutil
from datetime import date
from . import Base, fetch_session
#from .genomeproject import GenomeProject
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

    def __str__(self):
        return "Version(): {}, is_current {}, dl_directory: {}".format(self.version_id, self.is_current, self.dl_directory)

    '''
    Fetch the version_id of the latest (newest) version of microbedb

    None if no versions exist
    '''
    @classmethod
    def latest(cls):
        session = fetch_session()
        try:
            return session.query(Version).order_by(desc(Version.version_id)).first().version_id
        except:
            return None

    '''
    Fetch the version_id of the current (live) version of microbedb

    None if no versions exist
    '''
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

        d = date.today()
        datestr = d.strftime("%Y-%m-%d")

        v.dl_directory = os.path.join(cfg.basedir, 'Bacteria_' + datestr)

        session.commit()

        # Special case for when we're first initializing microbedb
        if not Version.current():
            Version.set_current(v.version_id)

        return v

    '''
    Fetch the path that points to the current version of microbedb
    '''
    @classmethod
    def fetch_default_path(cls):
        cfg = microbedb.config_singleton.getConfig()

        return os.path.join(cfg.basedir, "Bacteria")

    '''
    Fetch a named version of microbedb

    TODO: allow tagging of versions with a name beyond
    latest and current
    '''
    @classmethod
    def fetch(cls, version):
        global logger
        logger.debug("Version.fetch: {}".format(version))

        if version == 'current':
            version = Version.current()
        elif version == 'latest':
            version = Version.latest()

        return int(version)

    '''
    Fetch the path for a given version_id of microbedb

    Return None if not found
    '''
    @classmethod
    def fetch_path(cls, version):
        version = cls.fetch(version)

        session = fetch_session()

        try:

            return session.query(Version).filter(Version.version_id == version).first().dl_directory
        except:
            return None

    '''
    Set the default directory symlink to the given version
    '''
    @classmethod
    def set_default_directory(cls, version):
        global logger
        version = cls.fetch(version)
        if not version:
            logger.error("Error, we couldn't get the version")
            return False

        try:
            path = Version.fetch_path(version)
            default_path = Version.fetch_default_path()

            if path and os.path.exists(path):
                if os.path.islink(default_path):
                    os.unlink(default_path)
                elif os.path.exists(default_path):
                    shutil.rmtree(default_path)
                else:
                    logger.error("Default path doesn't exist, why was this? ({})".format(default_path))

                os.symlink(path, default_path)
                
            return True

        except Exception as e:
            logger.exception("Error changing symlink for default path")
            return False

    '''
    Set the current version of microbedb to the given version_id and
    change the path for the static directory name as needed
    '''
    @classmethod
    def set_current(cls, version):
        global logger
        version = cls.fetch(version)
        if not version:
            logger.error("Error, we couldn't get the version!")
            return False

        session = fetch_session()

        try:
            for v in session.query(Version).filter(Version.is_current == True):
                v.is_current = False

            # And now get the requested version and update it if we fine it
            v = session.query(Version).filter(Version.version_id == version).first()
            if v:
                v.is_current = True
                logger.info("New live version is {}".format(version))

            session.commit()

            Version.set_default_directory(version)

            return True

        except Exception as e:
            logger.exception("Error setting new current version")
            session.rollback()
            return False

    '''
    Remove a version of MicrobeDB, including all the GenomeProjects and
    Replicons.  Remove the flat files if requested.
    '''
    @classmethod
    def remove_version(cls, version, remove_files=False):
        global logger
        version = cls.fetch(version)
        if not version:
            logger.error("We couldn't find the version to remove")
            raise Exception("Couldn't find version to remove")

        session = fetch_session()

        logger.info("Removing MicrobeDB version {}, remove files: {}".format(version, remove_files))

        try:
#            for gp in session.query(GenomeProject).filter(GenomeProject.version_id == version):
#                GenomeProject.remove_gp(gp.gpv_id, remove_files=remove_files)

            update_current = False
            if version == Version.current():
                # Uh-oh, this is the current version, we'll have
                # to set a new current version
                logger.debug("This version {} is the current".format(version))
                update_current = True

            logger.info("Removing version {}".format(version))
            v_obj = session.query(Version).filter(Version.version_id == version).first()

            if remove_files and os.path.exists(v_obj.dl_directory):
                logger.debug("Removing directory for version {}, {}".format(version, v_obj.dl_directory))
                shutil.rmtree(v_obj.dl_directory)

            session.delete(v_obj)
            session.commit()

            if update_current:
                new_current = Version.latest()
                logger.info("Updating version {} as new current version".format(new_current))
                Version.set_current(new_current)

        except Exception as e:
            logger.exception("Error removing MicrobeDB version {}".format(version))
            raise e

    '''
    Make the path for a given version_id of microbedb.

    Return True if successful, otherwise False
    '''
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
