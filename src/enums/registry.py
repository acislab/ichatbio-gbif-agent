"""
Registry Parameters Enums

This module contains enums for registry-related API parameters based on the GBIF OpenAPI specification.
"""

from util_types import ParameterEnum


class DatasetTypeEnum(ParameterEnum):
    """Dataset type enumeration"""
    OCCURRENCE = "OCCURRENCE"
    CHECKLIST = "CHECKLIST"
    METADATA = "METADATA"
    SAMPLING_EVENT = "SAMPLING_EVENT"


class DatasetSubtypeEnum(ParameterEnum):
    """Dataset subtype enumeration"""
    TAXONOMIC_AUTHORITY = "TAXONOMIC_AUTHORITY"
    NOMENCLATOR_AUTHORITY = "NOMENCLATOR_AUTHORITY"
    INVENTORY_THEMATIC = "INVENTORY_THEMATIC"
    INVENTORY_REGIONAL = "INVENTORY_REGIONAL"
    GLOBAL_SPECIES_DATASET = "GLOBAL_SPECIES_DATASET"
    DERIVED_FROM_OCCURRENCE = "DERIVED_FROM_OCCURRENCE"
    SPECIMEN = "SPECIMEN"
    OBSERVATION = "OBSERVATION"


class EndpointTypeEnum(ParameterEnum):
    """Endpoint type enumeration"""
    EML = "EML"
    FEED = "FEED"
    WFS = "WFS"
    WMS = "WMS"
    TCS_RDF = "TCS_RDF"
    TCS_XML = "TCS_XML"
    DWC_ARCHIVE = "DWC_ARCHIVE"
    DIGIR = "DIGIR"
    DIGIR_MANIS = "DIGIR_MANIS"
    TAPIR = "TAPIR"
    BIOCASE = "BIOCASE"
    BIOCASE_XML_ARCHIVE = "BIOCASE_XML_ARCHIVE"
    OAI_PMH = "OAI_PMH"
    COLDP = "COLDP"
    CAMTRAP_DP = "CAMTRAP_DP"
    BIOM_1_0 = "BIOM_1_0"
    BIOM_2_1 = "BIOM_2_1"
    ACEF = "ACEF"
    TEXT_TREE = "TEXT_TREE"
    OTHER = "OTHER"


class MasterSourceTypeEnum(str, ParameterEnum):
    """The master source type of a GRSciColl institution or collection"""

    GRSCICOLL = "GRSCICOLL"
    GBIF_REGISTRY = "GBIF_REGISTRY"
    IH = "IH"

    def __str__(self):
        return self.value


class MasterSourceEnum(str, ParameterEnum):
    """Source attribute of MasterSourceMetadata"""

    DATASET = "DATASET"
    ORGANIZATION = "ORGANIZATION"
    IH_IRN = "IH_IRN"

    def __str__(self):
        return self.value


class IdentifierTypeEnum(str, ParameterEnum):
    """An identifier type for the identifier parameter"""

    URL = "URL"
    LSID = "LSID"
    HANDLER = "HANDLER"
    DOI = "DOI"
    UUID = "UUID"
    FTP = "FTP"
    URI = "URI"
    UNKNOWN = "UNKNOWN"
    GBIF_PORTAL = "GBIF_PORTAL"
    GBIF_NODE = "GBIF_NODE"
    GBIF_PARTICIPANT = "GBIF_PARTICIPANT"
    GRSCICOLL_ID = "GRSCICOLL_ID"
    GRSCICOLL_URI = "GRSCICOLL_URI"
    IH_IRN = "IH_IRN"
    ROR = "ROR"
    GRID = "GRID"
    CITES = "CITES"
    SYMBIOTA_UUID = "SYMBIOTA_UUID"
    WIKIDATA = "WIKIDATA"
    NCBI_BIOCOLLECTION = "NCBI_BIOCOLLECTION"
    ISIL = "ISIL"
    CLB_DATASET_KEY = "CLB_DATASET_KEY"
    RNC_COLOMBIA = "RNC_COLOMBIA"

    def __str__(self):
        return self.value


class SortByEnum(str, ParameterEnum):
    """Field to sort the results by"""

    NUMBER_SPECIMENS = "NUMBER_SPECIMENS"

    def __str__(self):
        return self.value


class SortOrderEnum(str, ParameterEnum):
    """Sort order to use with the sortBy parameter"""

    ASC = "ASC"
    DESC = "DESC"

    def __str__(self):
        return self.value
