import os
from . import Base, fetch_session
from .version import Version
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import make_transient
from sqlalchemy import exc as sqlalcexcept
import microbedb.config_singleton
import pprint

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
    prev_gpv = Column(Integer)

    @classmethod
    def find(cls, version='current', **kwargs);
        session = fetch_session()
        version = Version.fetch(version)

        # Try to fetch the GenomeProject if it exists
        try:
            gp = session.query(GenomeProject).filter(GenomeProject.assembly_accession == kwargs['assembly_accession'],
                                                             GenomeProject.asm_name == kwargs['asm_name'],
                                                             GenomeProject.version_id == version).first()

        except Exception as e:
            print "Error looking up GenomeProject: " + str(e)
            return None

        return gp

    @classmethod
    def find_or_create(cls, version='current', create_version='current', **kwargs):

        gp = GenomeProject.find(version=version, **kwargs)

        # We found a GenomeProject, return it
        if gp is not None:
            return gp, False

        # We didn't find a GenomeProject, so create one
        gp = GenomeProject.create_gp(version=create_version, **kwargs)

        if gp:
            return gp, True
        else:
            return None, False

    @classmethod
    def create_gp(cls, version='current', **kwargs):
        session = fetch_session()

        try:
            gp = GenomeProject()
            for col in GenomeProject.__table__columns:
                prop = gp.__mapper__._columntoproperty[col].key
                if prop in kwargs:
                    setattr(gp, prop, kwargs[prop])

            gp.version_id = Version.fetch(version)
            gp.gpv_directory = os.path.join(Version.fetch_path(gp.version_id), kwargs['assembly_accession'] + '_' + kwargs['asm_name'])

            session.add(gp)
            session.commit()

        except sqlalcexcept.IntegrityError as e:
            print "Insertion error: " + str(e)
            session.rollback()
            return None
        except Exception as e:
            print "Error creating GenomeProject obj: " + str(e)
            return None

        return gp



    @classmethod
    def findGP(cls, assembly_accession, asm_name, version='current'):

        session = fetch_session()
        version = Version.fetch(Version)

        try:            
            return session.query(GenomeProject).filter(assembly_accession=assembly_accession,
                                                             asm_name=asm_name,
                                                             version_id=version)
        except:
            return None

    def clone_gp(self, version='latest'):
        session = fetch_session()

        try:
            # See if we have a GenomeProject_Meta for this GP
            gp_meta = session.query(GenomeProject_Meta).filter(GenomeProject_Meta.gpv_id == self.gpv_id).first()

            old_path = self.gpv_directory
            old_gpv_id = self.gpv_id
            
            # Remove the GP object from the session and
            # unlink it's primary key
            session.expunge(self)
            make_transient(self)
            self.gpv_id = None
            
            # Update the session with the new version,
            # add the GP back to the session and commit it
            version = Version.fetch(version)
            self.version_id = version
            self.gpv_directory = os.path.join(Version.fetch_path(version), self.assembly_accession + '_' + self.asm_name)
            self.prev_gpv = old_gpv_id

            session.add(self)
            session.commit()

            # We've saved the object, make the file system symlink
            if os.path.exists(old_path):
                os.symlink(old_path, self.gpv_directory)

            # If we have a metadata object and we've successfully
            # updated ourself, clone the gp_meta object
            if gp_meta:
                gp_meta.clone_gpmeta(self.gpv_id)

        except Exception as e:
            print "Error cloning ession: " + str(e)
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
        session = fetch_session()

        try:
            # Remove the GP_Meta object from the session and
            # unlink it's primary key
            session.expunge(self)
            make_transient(self)
            self.gpv_id = gpv_id
            
            # Update the session,
            # add the GP back to the session and commit it
            session.add(self)
            session.commit()

        except Exception as e:
            print "Error cloning ession: " + str(e)
            session.rollback()
            raise e


class GenomeProject_Checksum(Base):
    __tablename__ = 'genomeproject_checksum'
#    gpv_id = Column(Integer, primary_key=True)
    version = Column(Integer, ForeignKey("Version.version_id"), primary_key=True)
    filename = Column(String(24), primary_key=True)
    checksum = Column(String(32))

    #
    # Check if we have a checksum for a file in the database and return
    # true or false if it matches
    #
    @classmethod
    def verify(cls, filename, checksum, version='current'):
        session = fetch_session()

        version = Version.fetch(version)

        # Try to fetch the GenomeProject if it exists
        try:
            gpcs = session.query(GenomeProject_Checksum).filter(GenomeProject_Checksum.version == version,
                                                                GenomeProject_Checksum.filename == filename).first()

        except Exception as e:
            print "Error looking up GenomeProject: " + str(e)
            return False
        
        # We found a checksum for this file, return if they match
        if gpcs is not None:
            return gpcs.checksum == checksum

        # Nothing found, return false
        return False
