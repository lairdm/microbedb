import os
import logging
import shutil
from . import Base, fetch_session
from .version import Version
from .replicon import Replicon
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
    taxid = Column(Integer)
    species_taxid = Column(Integer)
    org_name = Column(Text)
    infraspecific_name = Column(String(24))
    submitter = Column(Text)
    release_date = Column(Date)
    gpv_directory = Column(Text)
    prev_gpv = Column(Integer)

    def __str__(self):
        return "GenomeProject(): gpv_id {}, genome: {}/{}_{}, version: {}".format(self.gpv_id, self.genome_name, self.assembly_accession, self.asm_name, self.version_id)

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

            # We've saved the object, make the file system symlink
            # but first we have to check if we point to another base object,
            # if so find that path and link to it
            if self.prev_gpv:
                root_gp = session.query(GenomeProject).filter(GenomeProject.gpv_id == self.prev_gpv).first()

                if not root_gp:
                    logger.critical("We think we should have a root gpv_id {} but we can't find it, time to freak out".format(self.prev_gpv))
                    raise Exception("We can't find gpv_id {} but we ({}) seem to point to it".format(self.prev_gpv, self.gpv_id))

                # Now remember the path for the root GP so we can symlink to it
                old_path = root_gp.gpv_directory

            if os.path.exists(old_path) and self.verify_basedir():
                logger.debug("Making symlink from {} to {}".format(old_path, self.gpv_directory))
                os.symlink(old_path, self.gpv_directory)
            else:
                logger.error("We couldn't find the old path {} to make the symlink from, this is a problem".format(old_path))

            logger.debug("Committing self")
            session.add(self)
            session.commit()

            # If we have a metadata object and we've successfully
            # updated ourself, clone the gp_meta object
            if gp_meta:
                logger.debug("We have metadata, clone: {}".format(gp_meta))
#                print gp_meta
                gp_meta.clone_gpmeta(self.gpv_id) 
#                print gp_meta

           # Clone the replicons as we clone the GP record
            update_params = {'version_id': version, 'gpv_id': self.gpv_id}
            for rep in session.query(Replicon).filter(Replicon.gpv_id == old_gpv_id):
                logger.debug("Copying replicon {}".format(rep.rpv_id))
                rep.copy_and_update(**update_params)

            for gpcs in session.query(GenomeProject_Checksum).filter(GenomeProject_Checksum.gpv_id == old_gpv_id):
                logger.debug("Copying GP_Checksum for file {}".format(gpcs.filename))
                gpcs.copy_and_update(**update_params)

        except Exception as e:
            logger.exception("Exception cloning GenomeProject: " + str(e))
#            print "Error cloning ession: " + str(e)
            session.rollback()
            raise e

    '''
    Remove a GenomeProject, this involves removing all the associated replicons
    and the GP_Checksum and GP_Meta objects.  Also remove the flat files if
    requested
    '''
    @classmethod
    def remove_gp(cls, gpv_id, remove_files=False):
        global logger
        logger.info("Removing GenomeProject gpv_id {}".format(gpv_id))

        session = fetch_session()

        try:
            gp = session.query(GenomeProject).filter(GenomeProject.gpv_id == gpv_id).first()

            if not gp:
                logger.error("GP gpv_id {} not found".format(gpv_id))
                raise Exception("GenomeProject {} not found".format(gpv_id))

            # First we have to remove all the replicons
            for rep in session.query(Replicon).filter(Relicon.gpv_id == gpv_id):
                Replicon.remove_replicon(rep.rpv_id)

            # Next let's remove all the GP_Checksums
            for gpcs in session.query(GenomeProject_Checksum).filter(GenomeProject_Checksum.gpv_id == gpv_id):
                session.delete(gpcs)

            # Remove the GP_Meta object
            for gpmeta in session.query(GenomeProject_Meta).filter(GenomeProject_meta.gpv_id == gpv_id):
                session.delete(gpmeta)

            logger.debug("Committing changes for deleting GP_Checksum and GP_Meta objects")
            session.commit()

            # Now we need to untangle the symlinks if there are any
            if gp.prev_gpv:
                logger.debug("We're a leaf GP, no one should be pointing at us")
            else:
                # Someone could be pointing at us
                next_gp = None
                for gp_obj in session.query(GenomeProject).filter(GenomeProject.prev_gpv == gp.gpv_id).order_by(GenomeProject.gpv_id.asc()):
                    # For the first one, this will become the new root,
                    # all subsequent items should point here, and this new
                    # root shouldn't have a prev_gpv any longer
                    if not next_gp:
                        next_gp = gp_obj
                        next_gp.prev_gpv = None
                        if os.path.islink(next_gp.gpv_directory):
                            os.unlink(next_gp.gpv_directory)
                            logger.debug("Copying GP dir tree {}, {} to new root {}, {}".format(gp.gpv_id, gp.gpv_directory, next_gp.gpv_id, next_gp.gpv_directory))
                            shutil.copytree(gp.gpv_directory, next_gp.gpv_directory)
                        else:
                            logger.critical("We expected a symlink for gpv_id {}, path {} but it wasn't".format(next_gp.gpv_id, next_gp.gpv_directory))
                            
                        # Nothing more to do for this iteration
                        continue

                    # Now these following ones should point at the new root,
                    # this involves changing the pointer and symlink
                    logger.debug("Moving symlink for gpv_id {} to new root {}, {}".format(gpv_obj.gpv_id, next_gp.gpv_id, next_gp.gpv_directory))
                    if os.path.islink(gp_obj.gpv_directory):
                        os.unlink(gp_obj.gpv_directory)
                        os.symlink(next_gp.gpv_directory, gp_obj.gpv_directory)
                    else:
                        logger.critical("We expected a symlink for gpv_id {}, path {} but it wasn't".format(gp_obj.gpv_id, gp_obj.gpv_directory))

                # And if we found items that pointed to us, this
                # means we have rows to commit
                if next_gp:
                    session.commit()

            # Finally, remove the files if requested
            if remove_files:
                if os.path.islink(gp.gpv_directory):
                    logger.debug("Removing symlink for gpv_id {}, {}".format(gp.gpv_id, gp.gpv_directory))
                    os.unlink(gp.gpv_directory)
                else:
                    logger.debug("Removing tree for gpv_id {}, {}".format(gp.gpv_id, gp.gpv_directory))
                    shutil.rmtree(gp.gpv_directory)

            logger.debug("GenomeProject {} should now be removed".format(gpv_id))

        except Exception as e:
            logger.exception("Error removing GP {}".format(gpv_id))
            raise e

    #
    # Since NCBI stores genome projects grouped by species, we need to ensure
    # a genome's base directory is there
    #
    def verify_basedir(self):
        global logger

        basedir = os.path.join(Version.fetch_path(self.version_id), self.genome_name)

        try:
            if not os.path.exists(basedir):
                os.makedirs(basedir)

            return True

        except Exception as e:
            logger.exception("Error making basedir {} for gpv_id {}".format(basedir, self.gpv_id))
            return False

    def mkpath(self):
        global logger
        logger.debug("Making path for gpv_id {}, path {}".format(self.gpv_id, self.gpv_directory))

        try:
            if not os.path.exists(self.gpv_directory):
                os.makedirs(self.gpv_directory)

            return True

        except Exception as e:
            logger.exception("Error creating path for gpv_id {}, path {}".format(self.gpv_id, self.gpv_directory))
            return False


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

    def __str__(self):
        return "GenomeProject_Meta(): gpv_id {}, chromosome: {}, plasmid: {}, contig: {}".format(self.gpv_id, self.chromosome_num, self.plasmid_num, self.contig_num)

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

    def __str__(self):
        return "GenomeProject_Checksum(): gpv_id {}, version: {}, filename: {}".format(self.gpv_id, self.version, self.filename)

    def copy_and_update(self, **kwargs):
        global logger
        logger.info("Copy and update GP_Checksum file: {}, version: {}".format(self.filename, self.version))

        session = fetch_session()
        
        # Special case since version can be passed in as a string
        # such as 'latest' or 'current'
        if 'version_id' in kwargs:
            kwargs['version'] = Version.fetch(kwargs['version_id'])
        elif 'version' in kwargs:
            kwargs['version'] = Version.fetch(kwargs['version'])

        try:
            # Create a GP_Checksum object and begin copying fields
            gpcs = GenomeProject_Checksum()

            for col in GenomeProject_Checksum.__table__.columns:
                prop = gpcs.__mapper__._columntoproperty[col].key
                if prop in kwargs:
                    setattr(gpcs, prop, kwargs[prop])
                elif getattr(self, prop):
                    setattr(gpcs, prop, getattr(self, prop))
                    
            logger.debug("Committing GP_Checksum: " + str(gpcs))
            session.add(gpcs)
            session.commit()

            return gpcs

        except sqlalcexcept.IntegrityError as e:
            logger.exception("GP_Checksum insertion error (IntegrityError): " + str(e))
            session.rollback()
            return None
        except Exception as e:
            logger.exception("Unknown error creating GP_Checksum: " + str(e))
            return None


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
                logger.debug("Comparing db version: {} to ftp version: {}".format(gpcs.checksum, checksum))
                return gpcs.checksum == checksum

            # Nothing found, return false
            logger.debug("Didn't find a checksum for {}, version {}".format(filename, version))
            return False

        except Exception as e:
            logger.exception("Error checking checksum: " + str(e))
#            print "Error looking up GenomeProject: " + str(e)
            return False
