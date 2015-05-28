import os
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

class GenomeProject(Base):
    __tablename__ = 'genomeproject'
    gpv_id = Column(Integer, primary_key=True)
    assembly_accession = Column(String(16), nullable=False)
    asm_name = Column(String(12), nullable=False)
    genome_name = Column(Text)
    version_id = Column(Integer, default=0)
    bioproject = Column(String(14))
    biosample = Column(String(14))
    taxon_id = Column(Integer)
    org_name = Column(Text)
    infraspecific_name = Column(String(24))
    submitter = Column(Text)
    release_date = Column(Date)
    gpv_directory = Column(Text)
    prev_gpv = Column(Integer)

    @classmethod
    def find(cls, version='current', **kwargs):
        global logger
        logger.info("Searching for GenomeProject, version: {}, args: ".format(version) + str(kwargs))

        session = fetch_session()
        version = Version.fetch(version)

        # Try to fetch the GenomeProject if it exists
        try:
            gp = session.query(GenomeProject).filter(GenomeProject.assembly_accession == kwargs['assembly_accession'],
                                                             GenomeProject.asm_name == kwargs['asm_name'],
                                                             GenomeProject.version_id == version).first()

        except Exception as e:
            logger.exception("Error looking up GenomeProject, " + str(e))
#            print "Error looking up GenomeProject: " + str(e)
            return None

        return gp

    @classmethod
    def find_or_create(cls, version='current', create_version='current', **kwargs):
        global logger

        logger.info("Searching for GenomeProject or creating, version: {}, create_version: {}, args: ".format(version, create_version) + str(kwargs))

        gp = GenomeProject.find(version=version, **kwargs)

        # We found a GenomeProject, return it
        if gp is not None:
            logger.debug("Found GenomeProject")
            return gp, False

        # We didn't find a GenomeProject, so create one
        logger.info("GenomeProject not found, creating")
        gp = GenomeProject.create_gp(version=create_version, **kwargs)

        if gp:
            return gp, True
        else:
            return None, False

    @classmethod
    def create_gp(cls, version='current', **kwargs):
        global logger
        logger.info("Creating GenomeProject, version: {}, args: ".format(version) + str(kwargs))

        session = fetch_session()

        try:
            gp = GenomeProject()
            for col in GenomeProject.__table__.columns:
                prop = gp.__mapper__._columntoproperty[col].key
                if prop in kwargs:
                    setattr(gp, prop, kwargs[prop])

            gp.version_id = Version.fetch(version)
            gp.gpv_directory = os.path.join(Version.fetch_path(gp.version_id), kwargs['genome_name'], kwargs['assembly_accession'] + '_' + kwargs['asm_name'])

            logger.debug("Committing GenomeProject: " + str(gp))
            session.add(gp)
            session.commit()

        except sqlalcexcept.IntegrityError as e:
            logger.exception("GP insertion error (IntegrityError): " + str(e))
#            print "Insertion error: " + str(e)
            session.rollback()
            return None
        except Exception as e:
            logger.exception("Unknown error creating GenomeProject: " + str(e))
#            print "Error creating GenomeProject obj: " + str(e)
            return None

        return gp



    @classmethod
    def findGP(cls, assembly_accession, asm_name, version='current'):
        global logger
        logger.info("Searching for GenomeProject, assembly_accession: {}, asm_name: {}, version: {}, args: ".format(assembly_accession, asm_name, version))

        session = fetch_session()
        version = Version.fetch(Version)

        try:            
            return session.query(GenomeProject).filter(assembly_accession=assembly_accession,
                                                             asm_name=asm_name,
                                                             version_id=version)
        except Exception as e:
            logger.exception("Error searching for GP: " + str(e))
            return None

    def clone_gp(self, version='latest'):
        global logger
        logger.info("Cloning GenomeProject {}, version: {}".format(self.gpv_id, version))

        session = fetch_session()

        try:
            # See if we have a GenomeProject_Meta for this GP
            logger.debug("Attempting to clone metadata")
            gp_meta = session.query(GenomeProject_Meta).filter(GenomeProject_Meta.gpv_id == self.gpv_id).first()

            old_path = self.gpv_directory
            old_gpv_id = self.gpv_id
            
            # Remove the GP object from the session and
            # unlink it's primary key
            logger.debug("Expunging ourself from the session")
            session.expunge(self)
            make_transient(self)
            self.gpv_id = None
            
            # Update the session with the new version,
            # add the GP back to the session and commit it
            version = Version.fetch(version)
            self.version_id = version
            self.gpv_directory = os.path.join(Version.fetch_path(version), self.genome_name, self.assembly_accession + '_' + self.asm_name)
            self.prev_gpv = old_gpv_id

            logger.debug("Committing self")
            session.add(self)
            session.commit()

            rep_params = {'version_id': version, 'gpv_id': self.gpv_id}
            for rep in session.query(Replicon).filter(Replicon.gpv_id == old_gpv_id):
                logger.debug("Copying replicon {}".format(rep.rpv_id))
                rep.copy_and_update(**rep_params)

            # We've saved the object, make the file system symlink
            if os.path.exists(old_path):
                logger.debug("Making symlink from {} to {}".format(old_path, self.gpv_directory))
                os.symlink(old_path, self.gpv_directory)

            # If we have a metadata object and we've successfully
            # updated ourself, clone the gp_meta object
            if gp_meta:
                logger.debug("We have metadata, clone!")
                gp_meta.clone_gpmeta(self.gpv_id)

        except Exception as e:
            logger.exception("Exception cloning GenomeProject: " + str(e))
#            print "Error cloning ession: " + str(e)
            session.rollback()
            raise e

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
    plasmid_num = Column(Integer, default=0)
    contig_num = Column(Integer, default=0)

    def clone_gpmeta(self, gpv_id):
        global logger
        logger.info("Cloning GenomeProject_Meta, gpv_id: {}".format(gpv_id))

        session = fetch_session()

        try:
            # Remove the GP_Meta object from the session and
            # unlink it's primary key
            logger.debug("Expunging self (meta)")
            session.expunge(self)
            make_transient(self)
            self.gpv_id = gpv_id
            
            # Update the session,
            # add the GP back to the session and commit it
            logger.debug("Committing self (meta)")
            session.add(self)
            session.commit()

        except Exception as e:
            logger.exception("Error cloning Meta: " + str(e))
#            print "Error cloning ession: " + str(e)
            session.rollback()
            raise e

    @classmethod
    def create_or_update(cls, gpv_id, **kwargs):
        global logger
        logger.info("Create or update GP_Meta {}, args: ".format(gpv_id) + str(kwargs))

        session = fetch_session()

        try:
            gpmeta = session.query(GenomeProject_Meta).filter(GenomeProject_Meta.gpv_id == gpv_id).first()

            if not gpmeta:
                logger.debug("Didn't find GP_Meta for gpv_id {}".format(gpv_id))
                gpmeta = GenomeProject_Meta(gpv_id=gpv_id)

            # Now cycle through the columns we were given and update if they exist in the table
            for col in GenomeProject_Meta.__table__.columns:
                prop = gpmeta.__mapper__._columntoproperty[col].key
                if prop in kwargs:
                    setattr(gpmeta, prop, kwargs[prop])

            logger.debug("Committing gp_meta changes")
            session.add(gpmeta)
            session.commit()

            return gpmeta

        except Exception as e:
            logger.exception("Error updating gp_meta obj for gpv_id {}: ".format(gpv_id) + str(e))
            session.rollback()
            raise e

class GenomeProject_Checksum(Base):
    __tablename__ = 'genomeproject_checksum'
#    gpv_id = Column(Integer, primary_key=True)
    version = Column(Integer, primary_key=True)
    filename = Column(String(24), primary_key=True)
    checksum = Column(String(32))
    gpv_id = Column(Integer)

    #
    # Check if we have a checksum for a file in the database and return
    # true or false if it matches
    #
    @classmethod
    def verify(cls, filename, checksum, version='current'):
        global logger
        logger.info("Verifying checksum, filename: {}, checksum: {}, version: {}".format(filename, checksum, version))
        session = fetch_session()

        version = Version.fetch(version)

        # Try to fetch the GenomeProject if it exists
        try:
            gpcs = session.query(GenomeProject_Checksum).filter(GenomeProject_Checksum.version == version,
                                                                GenomeProject_Checksum.filename == filename).first()
        
            # We found a checksum for this file, return if they match
            if gpcs is not None:
                return gpcs.checksum == checksum

            # Nothing found, return false
            return False

        except Exception as e:
            logger.exception("Error checking checksum: " + str(e))
#            print "Error looking up GenomeProject: " + str(e)
            return False
