--
-- Table structure for table `gene`
--

CREATE TABLE IF NOT EXISTS `gene` (
  `gene_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `rpv_id` int(10) unsigned NOT NULL DEFAULT '0',
  `version_id` int(10) unsigned NOT NULL DEFAULT '0',
  `gpv_id` int(10) unsigned NOT NULL DEFAULT '0',
  `gid` int(10) unsigned DEFAULT '0',
  `pid` int(10) unsigned DEFAULT '0',
  `protein_accnum` char(12) DEFAULT '',
  `gene_type` enum('CDS','tRNA','rRNA','ncRNA','misc_RNA','tmRNA') DEFAULT NULL,
  `gene_start` int(11) DEFAULT '0',
  `gene_end` int(11) DEFAULT '0',
  `gene_length` int(11) DEFAULT '0',
  `gene_strand` enum('+','-','1','-1','0') DEFAULT NULL,
  `gene_name` tinytext,
  `locus_tag` tinytext,
  `gene_product` text,
  PRIMARY KEY (`gene_id`),
  KEY `gpv_id` (`gpv_id`),
  KEY `rpv_id` (`rpv_id`),
  KEY `pid_version` (`pid`,`version_id`),
  KEY `protein_accnum` (`version_id`,`protein_accnum`),
  KEY `locus_tag` (`locus_tag`(30))
);

--
-- Table structure for table `genomeproject`
--

CREATE TABLE IF NOT EXISTS `genomeproject` (
  `gpv_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `assembly_accession` varchar(16) CHARACTER SET latin1 NOT NULL,
  `asm_name` varchar(12) CHARACTER SET latin1 NOT NULL,
  `genome_name` text COLLATE utf8_unicode_ci NOT NULL,
  `version_id` int(10) unsigned DEFAULT '0',
  `bioproject` varchar(14) CHARACTER SET latin1 DEFAULT NULL,
  `biosample` varchar(14) CHARACTER SET latin1 DEFAULT NULL,
  `taxid` int(10) unsigned DEFAULT NULL,
  `species_taxid` int(11) DEFAULT NULL,
  `org_name` text CHARACTER SET latin1,
  `infraspecific_name` varchar(24) CHARACTER SET latin1 DEFAULT NULL,
  `submitter` text CHARACTER SET latin1,
  `release_date` date DEFAULT NULL,
  `gpv_directory` text CHARACTER SET latin1,
  `filename` varchar(50) DEFAULT NULL,
  `file_types` text COLLATE utf8_unicode_ci,
  `prev_gpv` int(11) DEFAULT NULL,
  PRIMARY KEY (`gpv_id`),
  UNIQUE KEY `assembly_index` (`assembly_accession`,`asm_name`,`version_id`),
  KEY `versions` (`version_id`)
) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Table structure for table `genomeproject_checksum`
--

CREATE TABLE IF NOT EXISTS `genomeproject_checksum` (
  `version` int(10) unsigned NOT NULL,
  `filename` varchar(64) CHARACTER SET latin1 NOT NULL DEFAULT '',
  `checksum` varchar(32) CHARACTER SET latin1 DEFAULT NULL,
  `gpv_id` int(11) NOT NULL,
  PRIMARY KEY (`version`,`filename`)
) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Table structure for table `genomeproject_meta`
--

CREATE TABLE IF NOT EXISTS `genomeproject_meta` (
  `gpv_id` int(10) unsigned NOT NULL,
  `gram_stain` enum('+','-','neither','unknown') CHARACTER SET latin1 DEFAULT 'unknown',
  `genome_gc` float(4,2) DEFAULT '0.00',
  `patho_status` enum('pathogen','nonpathogen','unknown') CHARACTER SET latin1 DEFAULT 'unknown',
  `disease` text CHARACTER SET latin1,
  `genome_size` float(4,2) DEFAULT '0.00',
  `pathogenic_in` text CHARACTER SET latin1,
  `temp_range` enum('unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic') CHARACTER SET latin1 DEFAULT 'unknown',
  `habitat` enum('unknown','host-associated','aquatic','terrestrial','specialized','multiple''unknown','cryophilic','psychrophilic','mesophilic','thermophilic','hyperthermophilic') CHARACTER SET latin1 DEFAULT 'unknown',
  `shape` text CHARACTER SET latin1,
  `arrangement` text CHARACTER SET latin1,
  `endospore` enum('yes','no','unknown') CHARACTER SET latin1 DEFAULT 'unknown',
  `motility` enum('yes','no','unknown') CHARACTER SET latin1 DEFAULT 'unknown',
  `salinity` text CHARACTER SET latin1,
  `oxygen_req` enum('unknown','aerobic','microaerophilic','facultative','anaerobic') CHARACTER SET latin1 DEFAULT 'unknown',
  `chromosome_num` int(10) unsigned DEFAULT '0',
  `plasmid_num` int(10) unsigned DEFAULT '0',
  `contig_num` int(10) unsigned DEFAULT '0',
  PRIMARY KEY (`gpv_id`)
) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Table structure for table `replicon`
--

CREATE TABLE IF NOT EXISTS `replicon` (
  `rpv_id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `gpv_id` int(10) unsigned NOT NULL DEFAULT '0',
  `version_id` int(10) unsigned NOT NULL DEFAULT '0',
  `rep_accnum` char(14) DEFAULT NULL,
  `rep_version` int(10) DEFAULT '1',
  `definition` text,
  `rep_type` enum('chromosome','plasmid','contig') DEFAULT NULL,
  `rep_ginum` tinytext,
  `file_name` text,
  `file_types` text COLLATE utf8_unicode_ci,
  `cds_num` int(10) unsigned DEFAULT '0',
  `gene_num` int(10) unsigned DEFAULT '0',
  `rep_size` int(10) unsigned DEFAULT '0',
  `rna_num` int(10) unsigned DEFAULT '0',
  PRIMARY KEY (`rpv_id`),
  KEY `version` (`version_id`),
  KEY `gpv_id` (`gpv_id`),
  KEY `rep_accnum` (`rep_accnum`),
  KEY `version_and_rep_type` (`version_id`,`rep_type`),
  KEY `type_index` (`rep_type`)
) DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci;

--
-- Table structure for table `taxonomy`
--

CREATE TABLE IF NOT EXISTS `taxonomy` (
  `taxon_id` int(10) unsigned NOT NULL,
  `superkingdom` tinytext,
  `phylum` tinytext,
  `tax_class` tinytext,
  `order` tinytext,
  `family` tinytext,
  `genus` tinytext,
  `species` tinytext,
  `other` tinytext,
  `synonyms` tinytext,
  PRIMARY KEY (`taxon_id`)
) DEFAULT CHARSET=latin1;

--
-- Table structure for table `version`
--

CREATE TABLE IF NOT EXISTS `version` (
  `version_id` int(11) NOT NULL AUTO_INCREMENT,
  `dl_directory` text,
  `version_date` date DEFAULT NULL,
  `used_by` text,
  `is_current` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`version_id`)
) DEFAULT CHARSET=latin1;
