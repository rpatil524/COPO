# FS - 18/8/2020
# this module contains lookups and mappings pertaining to DTOL functionality
# such as validation enumerations and mappings between different field names
DTOL_ENUMS = {
    "GAL": [
        "SANGER INSTITUTE",
        "UNIVERSITY OF OXFORD",
        "MARINE BIOLOGICAL ASSOCIATION",
        "UNIVERSITY OF CAMBRIDGE",
        "UNIVERSITY OF EDINBURGH",
        "ROYAL BOTANIC GARDENS KEW",
        "ROYAL BOTANIC GARDEN EDINBURGH",
        "EARLHAM INSTITUTE",
        "NATURAL HISTORY MUSEUM"
    ],
    "SPECIMEN_ID_RISK": [
        "Y",
        "N"
    ],
    "SEX": [
        "FEMALE",
        "MALE",
        "HERMAPHRODITE",
        "UNKNOWN"
    ],
    "LIFESTAGE": [
        "ADULT",
        "EGG",
        "JUVENILE",
        "LARVA",
        "PUPA",
        "SPOROPHYTE",
        "GAMETOPHYTE",
        "EMBRYO",
        "ZYGOTE",
        "SPORE-BEARING STRUCTURE",
        "VEGETATIVE STRUCTURE",
        "MYCELIUM"
    ],
    "HAZARD_GROUP": [
        "CL1",
        "CL2",
        "CL3",
        "UNKNOWN"
    ],
    "REGULATORY_COMPLIANCE": [
        "Y",
        "N"
    ],
    "ORGANISM_PART": [
        "BLOOD",
        "WHOLE",
        "HEAD",
        "ABDOMEN",
        "THORAX",
        "CEPHALOTHORAX",
        "LEG(S)",
        "HEAD/THORAX",
        "THORAX/ABDOMEN",
        "MYCELIUM",
        "MYCORRHIZA",
        "SPORE-BEARING STRUCTURE",
        "HOLDFAST",
        "STIPE",
        "CAP",
        "GILLS",
        "THALLUS",
        "LEAF",
        "FLOWER",
        "BLADE"
    ],
    "EASE_OF_SPECIMEN_COLLECTION": [
        "EASY",
        "MODERATE",
        "DIFFICULT",
        "EASY BUT SEASONAL",
        "MODERATE BUT SEASONAL",
        "DIFFICULT AND SEASONAL"
    ],
    "TO_BE_USED_FOR": [
        "RNAseq",
        "REFERENCE GENOME",
        "RESEQUENCING(POPGEN)",
        "BARCODING ONLY"
    ]
}
DTOL_ENA_MAPPINGS = {
    "ORGANISM_PART": {
        "ena": "organism part"
    },
    "LIFESTAGE": {
        "ena": "lifestage"
    },
    "profile.title": {
        "ena": "project name"
    },
    "COLLECTED_BY": {
        "ena": "collected_by"
    },
    "DATE_OF_COLLECTION": {
        "ena": "collection date"
    },
    "COLLECTION_LOCATION_1": {
        "info": "split COLLECTION_LOCATION on first '|' and put left hand side here (should be country)",
        "ena": "geographic location (country and/or sea)"
    },
    "DECIMAL_LATITUDE": {
        "ena": "geographic location (latitude)"
    },
    "DECIMAL_LONGITUDE": {
        "ena": "geographic location (longitude)"
    },
    "COLLECTION_LOCATION_2": {
        "info": "split COLLECTION_LOCATION on first '|' and put right hand side here (should be a list of '|' separated locations)",
        "ena": "geographic location (region and locality)"
    },
    "IDENTIFIED_BY": {
        "ena": "identified_by"
    },
    "DEPTH": {
        "ena": "geographic location (depth)"
    },
    "ELEVATION": {
        "ena": "geographic location (elevation)"
    },
    "HABITAT": {
        "ena": "habitat"
    },
    "IDENTIFIER_AFFLIATION": {
        "ena": "identifier_affiliation"
    },
    "SEX": {
        "ena": "sex"
    },
    "RELATIONSHIP": {
        "ena": "relationship"
    },
    "COLLECTOR_AFFILIATION": {
        "ena": "collecting institution"
    },
    "GAL": {
        "ena": "GAL"
    },
    "VOUCHER_ID": {
        "ena": "specimen_voucher"
    },
    "SPECIMEN_ID": {
        "ena": "specimen_id"
    },
    "GAL_SAMPLE_ID": {
        "ena": "GAL_sample_id"
    },
    "CULTURE_OR_STRAIN_ID": {
        "ena": "culture_or_strain_id"
    }
}
