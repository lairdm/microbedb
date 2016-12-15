import os
import logging
import shutil
import requests, sys
import xml.etree.ElementTree as ET
from . import Base, fetch_session
#from .genomeproject import GenomeProject
from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import desc
from sqlalchemy.sql import func
import microbedb.config_singleton
import pprint

logger = logging.getLogger(__name__)

class Taxonomy(Base):
    __tablename__ = 'taxonomy'
    taxon_id = Column(Integer, primary_key=True)
    superkingdom = Column(String(255))
    phylum = Column(String(255))
    tax_class = Column(String(255)) # Had to use tax_class since class is a reserved word
    order = Column(String(255))
    family = Column(String(255))
    genus = Column(String(255))
    species = Column(String(255))
    other = Column(String(255))
    synonyms = Column(String(255))

    def __str__(self):
        return "Taxonomy(): taxon_id: {}"

    @classmethod
    def find_or_create(cls, taxid):
        global logger

        logger.info("Searching for taxid {}".format(taxid))

        session = fetch_session()

        try:
            tax = session.query(Taxonomy).filter(Taxonomy.taxon_id == taxid).first()

            if tax is not None:
                logger.debug("Found taxid {}".format(taxid))
                return tax

            tax = Taxonomy(taxon_id = taxid)

            lineage = cls.ncbi_fetch(taxid)
            # A little hack because of that reserved word
            if 'class' in lineage:
                lineage['tax_class'] = lineage['class']

            for col in Taxonomy.__table__.columns:
                prop = tax.__mapper__._columntoproperty[col].key
                if prop in lineage:
                    setattr(tax, prop, lineage[prop])

            logger.debug("Committing Taxonomy: " + str(tax))
            session.add(tax)
            session.commit()

            return tax

        except Exception as e:
            logger.exception("Error fetching or creating taxid {}".format(taxid))
            session.rollback()
            return None

    @classmethod
    def guess_gram(cls, taxid):
        global logger

        tax = cls.find_or_create(taxid)

        if not tax:
            logger.error("Couldn't find taxid {}".format(taxid))
            return None

        for rank in valid_ranks:
            lin = getattr(tax, rank)
            if lin and lin in gram_predictions:
                return gram_predictions[lin]

        return None
                    

    @classmethod
    def ncbi_fetch(cls, taxid, email="lairdm@sfu.ca", tool="microbedb"):
        global logger

        try:
            server = "https://eutils.ncbi.nlm.nih.gov/"
            ext = "/entrez/eutils/efetch.fcgi?db=taxonomy&id={taxid}&report=xml&mode=text&email={email}&tool={tool}"

            req_str = server + ext.format(taxid=taxid, email=email, tool=tool)

            r = requests.get(req_str)

            if not r.ok:
                r.raise_for_status()
                logger.error("Error fetching taxon information")
                return None

            # Parse and we know we won't to go one level down
            # to the Taxon tag
            root = ET.fromstring(r.text)
            root = root.find("Taxon")

            lineage = dict()

            # Parse through the lineage to find the classes
            lineageex = root.find("LineageEx")
            if not lineageex or not len(lineageex):
                logger.critical("No lineage tree for taxon {}".format(taxid))
                return None

            for tax in lineageex.findall("Taxon"):
                rank = tax.find("Rank")
                if rank.text in valid_ranks:
                    lineage[rank.text] = tax.find("ScientificName").text

            # Fetch the synonyms
            synonyms = cls.parse_synonyms(root)
            if synonyms:
                lineage['synonyms'] = synonyms

            # Find the other field
            rank = root.find("Rank")
            if rank.text == "no rank":
                lineage['other'] = root.find("ScientificName").text
            else:
                lineage[rank.text] = root.find("ScientificName").text

            return lineage

        except Exception as e:
            logger.exception("Error fetching taxonomy from ncbi")
            return None

    @classmethod
    def parse_synonyms(cls, root):

        names_tag = root.find("OtherNames")

        if not names_tag or not len(names_tag):
            return None

        synonyms = list()

        for equiv in names_tag.findall("EquivalentName"):
            synonyms.append(equiv.text)

        for synonym in names_tag.findall("Synonym"):
            synonyms.append(synonym.text)

        if synonyms:
            return '; '.join(synonyms)
        else:
            return None

# Valid ranks we'll accept for lineage classification
valid_ranks = ['superkingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']

gram_predictions = {'Acidobacteria': '-',
                    'Actinobacteria': '+',
                    'Aquificae': '-',
                    'Bacteroidetes': '-',
                    'Chlamydiae': '-',
                    'Chlorobi': '-',
                    'Chloroflexi': '+',
                    'Cyanobacteria': '-',
                    'Deinococcus-Thermus': '-',
                    'Dictyoglomi': '-',
                    'Elusimicrobia': '-',
                    'Firmicutes': '+',
                    'Fusobacteria': '-',
                    'Nitrospirae': '-',
                    'Planctomycetes': '-',
                    'Proteobacteria': '-',
                    'Spirochaetes': '-',
                    'Tenericutes': '-',
                    'Thermotogae': '-',
                    'Verrucomicrobia': '-'
                }
