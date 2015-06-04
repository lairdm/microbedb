import os
import logging
import shutil
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
    def fetch_default_path(cls):
        cfg = microbedb.config_singleton.getConfig()

        return os.path.join(cfg.basedir, "Bacteria")

    @classmethod
    def fetch(cls, version):

        if version == 'current':
            version = Version.current()
        elif version == 'latest':
            version = Version.latest()

        return int(version)

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
                if os.path.exists(default_path):
                    if os.path.islink(default_path):
                        os.unlink(default_path)
                    else:
                        shutil.rmtree(default_path)

                os.symlink(path, default_path)
                
            return True

        except Exception as e:
            logger.exception("Error changing symlink for default path")
            return False

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
            print Version.current()
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
