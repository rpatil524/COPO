# define parameters for repositories
import os

REPOSITORIES = {
    'ASPERA': {
        'resource_path': 'tools/reposit/aspera/Aspera Connect.app/Contents/Resources/',
        'user_token': os.environ['WEBIN_USER'],
        'password': os.environ['WEBIN_USER_PASSWORD'],
        'remote_path': ''

    },
    'IRODS': {
        'api': 'irods',
        'resource_path': '/tempZone/home/rods/copo-data',
    },
    'ORCID': {
        'api': 'orcid',
        'client_id': 'xxx',
        'client_secret': 'xxx', 
        'urls': {
            'ouath/token': 'https://api.sandbox.orcid.org/oauth/token?',
            'base_url': 'https://sandbox.orcid.org',
            'authorise_url': os.environ['ORCID_REDIRECT'],
            'redirect': 'copo',
        }
    },
    'ENA':{
        'urls':{
            'submission':{
                'test': 'https://www-test.ebi.ac.uk/ena/submit/drop-box/submit/',
                'production': 'https://www.ebi.ac.uk/ena/submit/drop-box/submit/'
            }
        }
    }
}

UI_CONFIG_SOURCES = {
    'INVESTIGATION_FILE_XML': 'https://raw.githubusercontent.com/ISA-tools/Configuration-Files/master'
                              '/isaconfig-default_v2014-01-16/investigation.xml',
    'STUDY_SAMPLE_FILE_XML': 'https://raw.githubusercontent.com/ISA-tools/Configuration-Files/master'
                             '/isaconfig-default_v2014-01-16/studySample.xml',

    'STUDY_ASSAY_GENOME_SEQ_FILE_XML': 'https://raw.githubusercontent.com/ISA-tools/Configuration-Files/master'
                                       '/isaconfig-default_v2014-01-16/genome_seq.xml',
    'STUDY_ASSAY_METAGENOME_SEQ_FILE_XML': 'https://raw.githubusercontent.com/ISA-tools/Configuration-Files/master'
                                           '/isaconfig-default_v2014-01-16/metagenome_seq.xml',
    'STUDY_ASSAY_TRANSCRIPTOME_ANALYSIS_FILE_XML': 'https://raw.githubusercontent.com/ISA-tools/Configuration-Files/master'
                                                   '/isaconfig-default_v2014-01-16/transcription_seq.xml'
}

WEB_SERVICES = {
    'COPO': {
        'get_id': 'http://v0514.nbi.ac.uk:1025/id/'
    }
}

DOI_SERVICES = {
    "base_url": "http://dx.doi.org/",
    "namespaces": {
        "DC": "http://purl.org/dc/terms/",
        "FOAF": "http://xmlns.com/foaf/0.1/"
    }
}

NCBI_SERVICES = {
    "PMC_APIS": {
        "doi_pmid_idconv": "http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={doi!s}&format=json",
        "pmid_doi_esummary": "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid!s}&retmode=json"
    }
}

EXPORT_LOCATIONS = {
    'ENA': {
        'export_path': '~/Desktop/'
    }
}
