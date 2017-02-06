'''
Library for various file manipulation in MicrobeDB
'''

import logging
import re, os, sys
from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC, generic_protein, generic_dna
import pprint

logger = logging.getLogger(__name__)

def find_extensions(path, prefix=None):
    global logger

    if not os.path.exists(path):
        logger.error("We can't find path {} when checking for extensions".format(path))
        return None

    try:
        files = [ f for f in os.listdir(path) if os.path.isfile(os.path.join(path,f)) and os.stat(os.path.join(path,f)).st_size > 0 ]

        exts = list()
        for file in files:
            # If we have a prefix, and if it doesn't match, skip
            if prefix and not re.search('^'+prefix, file):
                continue

            ext = os.path.splitext(file)[-1]
            if ext:
                exts.append(ext)

        logger.debug("Found file types: {}".format(exts))
        exts=list(set(exts))
        exts.sort()
    
        return " ".join(exts)

    except Exception as e:
        logger.exception("Error finding filename extensions")
        return None

def separate_genbank(genbank_file, fna_file, rep_accnum, path):
    global logger

    logger.info("Separating genbank file {} based on accnum {}, writing to {}".format(genbank_file, rep_accnum, path))

    if not os.path.exists(genbank_file):
        logger.critical("Genbank file {} doesn't exist".format(genbank_file))
        return False

    # Parse the genbank file and for each replicon in it
    # find ourself
    record = None
    with open(genbank_file, 'rU') as infile:
        for r in SeqIO.parse(infile, "genbank"):
            accnum, version = r.id.split(".")
            if accnum == rep_accnum:
                logger.debug("Found our genbank record for {}".format(rep_accnum))
                record = r
                break

    if not record:
        logger.critical("Can't find record for {} in genbank file {}".format(rep_accnum, genbank_file))
        return False

    # And because ncbi now separates the sequence from the genbank,
    # we need to grab the sequence and stich it in
    seq_record = None
    with open(fna_file, 'rU') as infile:
        for r in SeqIO.parse(infile, "fasta", alphabet=IUPAC.unambiguous_dna):
            accnum, version = r.id.split(".")
            if accnum == rep_accnum:
                logger.debug("Found our fna record for {}".format(rep_accnum))
                seq_record = r
                break

    if not seq_record:
        logger.critical("Can't find record for {} in fna file {}".format(rep_accnum, fna_file))
        return False

    # Put the sequence in to the genbank record
    record.seq = seq_record.seq    

    if not os.path.exists(path):
        logger.critical("We don't seem to have the path we want to write the files to: {}".format(path))

    # Now we write out the separate files, let's start with the genbank
    with open(os.path.join(path, rep_accnum) + '.gbk', 'w') as outfile:
        SeqIO.write(record, outfile, 'genbank')

    # And while we're here, make the fna file for the replicon
    with open(os.path.join(path, rep_accnum) + '.fna', 'w') as outfile:
        SeqIO.write(seq_record, outfile, 'fasta')

    # Next let's make the ffn and faa files
    # We're going to have to loop through twice either way,
    # either through the features once to make a hash then the hash,
    # or let's just go through the features twice and use the 
    # CDS records the first time for the faa file, then remember them
    # for our second loop for the ffn file
    proteins = dict()
    faa_records = []
    ptt_records = []
    organism = None
    if 'organism' in record.annotations:
        organism = record.annotations['organism']
    elif 'source' in record.annotations:
        organism = record.annotations['source']
    for feat in record.features:
        if feat.type == 'CDS':
            coords = str(feat.location.start+1) + ".." + str(feat.location.end)
            if 'translation' not in feat.qualifiers:
                logger.debug("No translation for feature at coords {}".format(coords))
                continue

            prot_seq = feat.qualifiers['translation'][0]

            id_str = []
            strand_str = '-' if feat.location.strand == -1 else '+'
            ptt_pieces = [coords, strand_str, str(len(prot_seq))]
            if 'db_xref' in feat.qualifiers:
                gi = find_xref(feat.qualifiers['db_xref'])
                if gi:
                    id_str.append("gi|{}".format(gi))
                    ptt_pieces.append(gi)
                else:
                    ptt_pieces.append('-')
            else:
                ptt_pieces.append('-')

            if 'gene' in feat.qualifiers:
                ptt_pieces.append(feat.qualifiers['gene'][0])
            else:
                ptt_pieces.append('-')

            if 'protein_id' in feat.qualifiers:
                for pid in feat.qualifiers['protein_id']:
                    id_str.append("ref|{}".format(pid))
                
            if 'locus_tag' in feat.qualifiers:
                for locus in feat.qualifiers['locus_tag']:
                    id_str.append("locus|{}".format(locus))
                ptt_pieces.append(feat.qualifiers['locus_tag'][0])
            else:
                ptt_pieces.append('-')
            
            # Finally append the coordinates
            if feat.location.strand == -1:
                id_str.append(":c{}".format(coords))
            else:
                id_str.append(":{}".format(coords))
            
            # And pad out the final three fields in the ptt line
            ptt_pieces.append('-')
            ptt_pieces.append('-')
            ptt_pieces.append(feat.qualifiers['product'][0])
            ptt_records.append("\t".join(ptt_pieces))

            # Build the faa header description piece
            description = feat.qualifiers['product'][0]
            if organism:
                description += " [{}]".format(organism)

            # Make the sequence object now that we have the identifier built
            seqreq = SeqRecord(Seq(prot_seq, generic_protein),
                               id="|".join(id_str),
                               description=description)
            # We should have a sequence now, append it for writing since
            # biopython doesn't seem to allow streaming writing
            faa_records.append(seqreq)

            # And save the information about the protein for when we 
            # circle around doing the genes for the ffn file
            proteins[coords] = id_str

    # Write out the faa records to the file
    with open(os.path.join(path, rep_accnum) + '.faa', 'w') as outfile:
        SeqIO.write(faa_records, outfile, 'fasta')

    # And clear the faa records to save memory
    faa_records = None

    # Write out the ptt records to the file
    with open(os.path.join(path, rep_accnum) + '.ptt', 'w') as outfile:
        outfile.write("{} - 1..{}\n".format(record.description, len(record.seq)))
        outfile.write("{} proteins\n".format(str(len(ptt_records))))
        outfile.write("\t".join(['Location', 'Strand', 'Length', 'PID', 'Gene', 'Synonym', 'Code', 'COG', 'Product']) + "\n")
        for ptt in ptt_records:
            outfile.write("{}\n".format(ptt))

    # Loop again looking for genes
    ffn_records = []
    for feat in record.features:
        if feat.type == 'gene':
            coords = str(feat.location.start+1) + ".." + str(feat.location.end)
            if coords not in proteins:
                logger.error("The gene at {} doesn't seem to have a corresponding protein record".format(coords))
                continue

            id_str = proteins[coords]
            ffn_seq = feat.extract(record.seq)

            # Make the sequence object now that we have the identifier built
            seqreq = SeqRecord(ffn_seq,
                               id="|".join(id_str),
                               description=record.description)

            # Append the sequence for writing out
            ffn_records.append(seqreq)

    # Write out the ffn records to the file
    with open(os.path.join(path, rep_accnum) + '.ffn', 'w') as outfile:
        SeqIO.write(ffn_records, outfile, 'fasta')

    return True

def find_xref(xrefs, xref_type="GI"):
    global logger

    try:
        for xref in xrefs:
            xtype, x = xref.split(':')
            if re.search('^'+xref_type, xref):
                return x

        return None

    except Exception as e:
        logger.exception("Error extracting xrefs from: " + str(xrefs))
        return None
