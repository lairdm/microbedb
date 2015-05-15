CREATE TABLE IF NOT EXISTS genomeproject (
  gpv_id int unsigned NOT NULL auto_increment,
  assembly_accession varchar(16) NOT NULL,
  asm_name varchar(12) NOT NULL,
  version_id int unsigned default 0,
  bioproject varchar(14),
  biosample varchar(14),
  taxon_id int unsigned,
  org_name text,
  infraspecific_name varchar(24),
  submitter text,
  release_date date,
  gpv_directory text,
  PRIMARY KEY (gpv_id),
  INDEX versions (version_id),
  UNIQUE assembly_index (assembly_accession, asm_name, version_id)
);

CREATE TABLE IF NOT EXISTS genomeproject_meta (
  gpv_id int unsigned NOT NULL,
  gram_stain enum('+','-','neither','unknown') DEFAULT 'unknown',
  genome_gc float(4,2) DEFAULT '0.00',
  patho_status enum('pathogen','nonpathogen','unknown') DEFAULT 'unknown',
  disease text,
  genome_size float(4,2) DEFAULT '0.00',
  pathogenic_in text,
  temp_range enum('unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic') DEFAULT 'unknown',
  habitat enum('unknown','host-associated','aquatic','terrestrial','specialized','multiple''unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic') DEFAULT 'unknown',
  shape text,
  arrangement text,
  endospore enum('yes','no','unknown') DEFAULT 'unknown',
  motility enum('yes','no','unknown') DEFAULT 'unknown',
  salinity text,
  oxygen_req enum('unknown','aerobic','microaerophilic','facultative','anaerobic') DEFAULT 'unknown',
  chromosome_num int(10) unsigned DEFAULT '0',
  plasmid_num int(10) unsigned DEFAULT '0',
  contig_num int(10) unsigned DEFAULT '0',
  PRIMARY KEY (gpv_id)
);

CREATE TABLE IF NOT EXISTS genomeproject_checksum (
  gpv_id int unsigned NOT NULL,
  filename varchar(24),
  checksum varchar(32),
  PRIMARY KEY (gpv_id, filename)
);
