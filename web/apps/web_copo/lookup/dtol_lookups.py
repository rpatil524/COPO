# FS - 18/8/2020
# this module contains lookups and mappings pertaining to DTOL functionality
# such as validation enumerations and mappings between different field names
DTOL_EXPORT_TO_STS_FIELDS = {
    "SERIES",
    "RACK_OR_PLATE_ID",
    "TUBE_OR_WELL_ID",
    "SPECIMEN_ID",
    "ORDER_OR_GROUP",
    "FAMILY",
    "GENUS",
    "TAXON_ID",
    "SCIENTIFIC_NAME",
    "LIFESTAGE",
    "SEX",
    "ORGANISM_PART",
    "GAL",
    "GAL_SAMPLE_ID",
    "COLLECTOR_SAMPLE_ID",
    "COLLECTED_BY",
    "COLLECTOR_AFFILIATION",
    "DATE_OF_COLLECTION",
    "COLLECTION_LOCATION",
    "DECIMAL_LATITUDE",
    "DECIMAL_LONGITUDE",
    "HABITAT",
    "DESCRIPTION_OF_COLLECTION_METHOD",
    "EASE_OF_SPECIMEN_COLLECTION",
    "IDENTIFIED_BY",
    "IDENTIFIER_AFFILIATION",
    "IDENTIFIED_HOW",
    "SPECIMEN_ID_RISK",
    "PRESERVED_BY",
    "PRESERVER_AFFILIATION",
    "PRESERVATION_APPROACH",
    "TIME_ELAPSED_FROM_COLLECTION_TO_PRESERVATION",
    "DATE_OF_PRESERVATION",
    "SIZE_OF_TISSUES_IN_TUBE",
    "TISSUE_REMOVED_FROM_BARCODING",
    "PLATE_ID_FOR_BARCODING",
    "TUBE_OR_WELL_ID_FOR_BARCODING",
    "TISSUE_FOR_BARCODING",
    "BARCODE_PLATE_PRESERVATIVE",
    "PURPOSE_OF_SPECIMEN",
    "HAZARD_GROUP",
    "REGULATORY_COMPLIANCE",
    "VOUCHER_ID",
    "biosampleAccession",
    "created_by",
    "time_created",
    "submissionAccession",
    "sraAccession",
    "manifest_id",
    "time_verified",
    "verified_by",
    "status"

}
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
    ],
    "COUNTRIES": [
        "AFGHANISTAN",
        "ALBANIA",
        "ALGERIA",
        "AMERICAN SAMOA",
        "ANDORRA",
        "ANGOLA",
        "ANGUILLA",
        "ANTARCTICA",
        "ANTIGUA AND BARBUDA",
        "ARCTIC OCEAN",
        "ARGENTINA",
        "ARMENIA",
        "ARUBA",
        "ASHMORE AND CARTIER ISLANDS",
        "ATLANTIC OCEAN",
        "AUSTRALIA",
        "AUSTRIA",
        "AZERBAIJAN",
        "BAHAMAS",
        "BAHRAIN",
        "BAKER ISLAND",
        "BALTIC SEA",
        "BANGLADESH",
        "BARBADOS",
        "BASSAS DA INDIA",
        "BELARUS",
        "BELGIUM",
        "BELIZE",
        "BENIN",
        "BERMUDA",
        "BHUTAN",
        "BOLIVIA",
        "BORNEO",
        "BOSNIA AND HERZEGOVINA",
        "BOTSWANA",
        "BOUVET ISLAND",
        "BRAZIL",
        "BRITISH VIRGIN ISLANDS",
        "BRUNEI",
        "BULGARIA",
        "BURKINA FASO",
        "BURUNDI",
        "CAMBODIA",
        "CAMEROON",
        "CANADA",
        "CAPE VERDE",
        "CAYMAN ISLANDS",
        "CENTRAL AFRICAN REPUBLIC",
        "CHAD",
        "CHILE",
        "CHINA",
        "CHRISTMAS ISLAND",
        "CLIPPERTON ISLAND",
        "COCOS ISLANDS",
        "COLOMBIA",
        "COMOROS",
        "COOK ISLANDS",
        "CORAL SEA ISLANDS",
        "COSTA RICA",
        "COTE D'IVOIRE",
        "CROATIA",
        "CUBA",
        "CURACAO",
        "CYPRUS",
        "CZECH REPUBLIC",
        "DEMOCRATIC REPUBLIC OF THE CONGO",
        "DENMARK",
        "DJIBOUTI",
        "DOMINICA",
        "DOMINICAN REPUBLIC",
        "EAST TIMOR",
        "ECUADOR",
        "EGYPT",
        "EL SALVADOR",
        "EQUATORIAL GUINEA",
        "ERITREA",
        "ESTONIA",
        "ETHIOPIA",
        "EUROPA ISLAND",
        "FALKLAND ISLANDS (ISLAS MALVINAS)",
        "FAROE ISLANDS",
        "FIJI",
        "FINLAND",
        "FRANCE",
        "FRENCH GUIANA",
        "FRENCH POLYNESIA",
        "FRENCH SOUTHERN AND ANTARCTIC LANDS",
        "GABON",
        "GAMBIA",
        "GAZA STRIP",
        "GEORGIA",
        "GERMANY",
        "GHANA",
        "GIBRALTAR",
        "GLORIOSO ISLANDS",
        "GREECE",
        "GREENLAND",
        "GRENADA",
        "GUADELOUPE",
        "GUAM",
        "GUATEMALA",
        "GUERNSEY",
        "GUINEA",
        "GUINEA-BISSAU",
        "GUYANA",
        "HAITI",
        "HEARD ISLAND AND MCDONALD ISLANDS",
        "HONDURAS",
        "HONG KONG",
        "HOWLAND ISLAND",
        "HUNGARY",
        "ICELAND",
        "INDIA",
        "INDIAN OCEAN",
        "INDONESIA",
        "IRAN",
        "IRAQ",
        "IRELAND",
        "ISLE OF MAN",
        "ISRAEL",
        "ITALY",
        "JAMAICA",
        "JAN MAYEN",
        "JAPAN",
        "JARVIS ISLAND",
        "JERSEY",
        "JOHNSTON ATOLL",
        "JORDAN",
        "JUAN DE NOVA ISLAND",
        "KAZAKHSTAN",
        "KENYA",
        "KERGUELEN ARCHIPELAGO",
        "KINGMAN REEF",
        "KIRIBATI",
        "KOSOVO",
        "KUWAIT",
        "KYRGYZSTAN",
        "LAOS",
        "LATVIA",
        "LEBANON",
        "LESOTHO",
        "LIBERIA",
        "LIBYA",
        "LIECHTENSTEIN",
        "LITHUANIA",
        "LUXEMBOURG",
        "MACAU",
        "MACEDONIA",
        "MADAGASCAR",
        "MALAWI",
        "MALAYSIA",
        "MALDIVES",
        "MALI",
        "MALTA",
        "MARSHALL ISLANDS",
        "MARTINIQUE",
        "MAURITANIA",
        "MAURITIUS",
        "MAYOTTE",
        "MEDITERRANEAN SEA",
        "MEXICO",
        "MICRONESIA",
        "MIDWAY ISLANDS",
        "MOLDOVA",
        "MONACO",
        "MONGOLIA",
        "MONTENEGRO",
        "MONTSERRAT",
        "MOROCCO",
        "MOZAMBIQUE",
        "MYANMAR",
        "NAMIBIA",
        "NAURU",
        "NAVASSA ISLAND",
        "NEPAL",
        "NETHERLANDS",
        "NEW CALEDONIA",
        "NEW ZEALAND",
        "NICARAGUA",
        "NIGER",
        "NIGERIA",
        "NIUE",
        "NORFOLK ISLAND",
        "NORTH KOREA",
        "NORTH SEA",
        "NORTHERN MARIANA ISLANDS",
        "NORWAY",
        "OMAN",
        "PACIFIC OCEAN",
        "PAKISTAN",
        "PALAU",
        "PALMYRA ATOLL",
        "PANAMA",
        "PAPUA NEW GUINEA",
        "PARACEL ISLANDS",
        "PARAGUAY",
        "PERU",
        "PHILIPPINES",
        "PITCAIRN ISLANDS",
        "POLAND",
        "PORTUGAL",
        "PUERTO RICO",
        "QATAR",
        "REPUBLIC OF THE CONGO",
        "REUNION",
        "ROMANIA",
        "ROSS SEA",
        "RUSSIA",
        "RWANDA",
        "SAINT HELENA",
        "SAINT KITTS AND NEVIS",
        "SAINT LUCIA",
        "SAINT PIERRE AND MIQUELON",
        "SAINT VINCENT AND THE GRENADINES",
        "SAMOA",
        "SAN MARINO",
        "SAO TOME AND PRINCIPE",
        "SAUDI ARABIA",
        "SENEGAL",
        "SERBIA",
        "SEYCHELLES",
        "SIERRA LEONE",
        "SINGAPORE",
        "SINT MAARTEN",
        "SLOVAKIA",
        "SLOVENIA",
        "SOLOMON ISLANDS",
        "SOMALIA",
        "SOUTH AFRICA",
        "SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS",
        "SOUTH KOREA",
        "SOUTHERN OCEAN",
        "SPAIN",
        "SPRATLY ISLANDS",
        "SRI LANKA",
        "SUDAN",
        "SURINAME",
        "SVALBARD",
        "SWAZILAND",
        "SWEDEN",
        "SWITZERLAND",
        "SYRIA",
        "TAIWAN",
        "TAJIKISTAN",
        "TANZANIA",
        "TASMAN SEA",
        "THAILAND",
        "TOGO",
        "TOKELAU",
        "TONGA",
        "TRINIDAD AND TOBAGO",
        "TROMELIN ISLAND",
        "TUNISIA",
        "TURKEY",
        "TURKMENISTAN",
        "TURKS AND CAICOS ISLANDS",
        "TUVALU",
        "USA",
        "UGANDA",
        "UKRAINE",
        "UNITED ARAB EMIRATES",
        "UNITED KINGDOM",
        "URUGUAY",
        "UZBEKISTAN",
        "VANUATU",
        "VENEZUELA",
        "VIET NAM",
        "VIRGIN ISLANDS",
        "WAKE ISLAND",
        "WALLIS AND FUTUNA",
        "WEST BANK",
        "WESTERN SAHARA",
        "YEMEN",
        "ZAMBIA",
        "ZIMBABWE",
        "NOT APPLICABLE",
        "NOT COLLECTED",
        "NOT PROVIDED",
        "RESTRICTED ACCESS"
    ]
}
DTOL_RULES = {
    "DATE_OF_COLLECTION": {
        "regex" : "(^[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?(/[0-9]{4}(-[0-9]{2}(-[0-9]{2}(T[0-9]{2}:[0-9]{2}(:[0-9]{2})?Z?([+-][0-9]{1,2})?)?)?)?)?$)|(^not collected$)|(^not provided$)|(^restricted access$)"
    },
    "DECIMAL_LATITUDE": {
        "regex" : "(^.*[+-]?[0-9]+.?[0-9]*.*$)|(^not collected$)|(^not provided$)|(^restricted access$)"
    },
    "DECIMAL_LONGITUDE": {
        "regex" : "(^.*[+-]?[0-9]+.?[0-9]*.*$)|(^not collected$)|(^not provided$)|(^restricted access$)"
    },
    "DEPTH": {
        "regex" : "(0|((0\.)|([1-9][0-9]*\.?))[0-9]*)([Ee][+-]?[0-9]+)?"
    },
    "ELEVATION": {
        "regex" : "[+-]?(0|((0\.)|([1-9][0-9]*\.?))[0-9]*)([Ee][+-]?[0-9]+)?"
    }
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
