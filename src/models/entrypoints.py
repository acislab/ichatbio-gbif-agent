from typing import List, Optional
from pydantic import Field

from src.models.base import ProductionBaseModel
from src import models

from src.enums.common import (
    ContinentEnum,
    LicenseEnum,
    CountryEnum,
)
from src.enums.species import (
    TaxonomicRankEnum,
    QueryFieldEnum,
)
from src.enums.registry import (
    DatasetTypeEnum,
    DatasetSubtypeEnum,
    EndpointTypeEnum,
)


class GBIFOccurrenceBaseParams(
    models.occurrences.TaxonomicFilters,
    models.occurrences.GeographicFilters,
    models.occurrences.TemporalFilters,
    models.occurrences.RecordIdentifiers,
    models.occurrences.DatasetCollectionFilters,
    models.occurrences.OrganismSpecimenFilters,
    models.occurrences.MediaSequenceFilters,
    models.occurrences.IdentificationFilters,
    models.occurrences.GeologicalFilters,
    models.occurrences.InvasiveSpeciesFilters,
    models.occurrences.ConservationFilters,
    models.occurrences.QualityFilters,
    models.occurrences.ProjectProgrammeFilters,
    models.occurrences.SearchFilters,
    models.occurrences.ExperimentalFilters,
    models.occurrences.HighLevelSearchFilters,
    models.common.PaginationParams,
):
    """
    Base parameters for GBIF occurrence operations.

    This model composes all common search and filter parameters from smaller,
    organized filter models:
    - TaxonomicFilters: Taxonomic classification and identification filters
    - GeographicFilters: Geographic location and spatial filters
    - TemporalFilters: Temporal (time-based) filters
    - RecordIdentifiers: Record identification and catalog information
    - DatasetCollectionFilters: Dataset, collection, and institution filters
    - OrganismSpecimenFilters: Organism and specimen characteristic filters
    - MediaSequenceFilters: Media and sequence-related filters
    - IdentificationFilters: Identification and recorder information filters
    - GeologicalFilters: Geological and stratigraphic filters
    - InvasiveSpeciesFilters: Invasive species and establishment filters
    - ConservationFilters: Conservation and threat status filters
    - QualityFilters: Data quality and issue filters
    - ProjectProgrammeFilters: Project and programme filters
    - SearchFilters: Full-text search and license filters
    - ExperimentalFilters: Experimental search options
    - HighLevelSearchFilters: High-level composite search filters
    - PaginationParams: Unified pagination parameters
    """

    limit: Optional[int] = Field(
        300,
        ge=0,
        le=4800,
        description="The page size (maximum number of records to retrieve). Cannot retrieve more than 4800",
    )

    offset: Optional[int] = Field(
        None,
        ge=0,
        le=100000,
        description="The page offest (how many records to skip)",
    )


class GBIFOccurrenceSearchParams(GBIFOccurrenceBaseParams):
    """Parameters for GBIF occurrence search - matches API structure"""

    pass


class GBIFOccurrenceFacetsParams(GBIFOccurrenceBaseParams, models.common.FacetParams):
    """
    Parameters for GBIF occurrence faceting.
    Extends GBIFOccurrenceBaseParams with FacetParams for faceting options.
    """

    # Override limit default for faceting (0 for facets only)
    limit: Optional[int] = Field(
        0, ge=0, le=300, description="Number of results per page (0 for facets only)"
    )


class GBIFSpeciesSearchParams(
    models.species.SearchFilters,
    models.species.DatasetFilters,
    models.species.TaxonomicFilters,
    models.species.NameFilters,
    models.species.EcologyFilters,
    models.species.QualityFilters,
    models.common.PaginationParams,
):
    """
    Parameters for GBIF species search.

    Full text search over name usages covering scientific and vernacular names,
    species descriptions, distribution and classification data.

    This model composes all search parameters from smaller, organized filter models:
    - SpeciesSearchFilters: Core search and query filters
    - SpeciesDatasetFilters: Dataset and checklist filters
    - SpeciesTaxonomicFilters: Taxonomic rank and classification filters
    - SpeciesNameFilters: Name type and nomenclatural status filters
    - SpeciesEcologyFilters: Ecological and conservation filters
    - SpeciesQualityFilters: Data quality and indexing issue filters
    - PaginationParams: Unified pagination parameters (supports page and offset)
    """

    pass


class GBIFSpeciesFacetsParams(GBIFSpeciesSearchParams, models.common.FacetParams):
    """
    Parameters for GBIF species faceting.

    Extends GBIFSpeciesSearchParams with FacetParams for faceting options and
    statistical analysis.
    """

    # Override limit default for faceting (0 for facets only)
    limit: Optional[int] = Field(
        0, ge=0, le=1000, description="Number of results per page (0 for facets only)"
    )


class GBIFSpeciesTaxonomicParams(ProductionBaseModel):
    """Parameters for GBIF species taxonomic information - retrieves comprehensive taxonomic data for a specific species"""

    key: Optional[int] = Field(
        None,
        description="The GBIF key (taxon key) for the species. This is a required parameter that uniquely identifies the species in the GBIF backbone.",
        examples=[5231190, 2476674, 2877951],
    )

    name: Optional[str] = Field(
        None,
        description="The scientific name of the species. This is a required parameter that uniquely identifies the species in the GBIF backbone.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    rank: Optional[TaxonomicRankEnum] = Field(
        None,
        description="The taxonomic rank of the species. This is an optional parameter that can be used to filter the results by taxonomic rank.",
        examples=[
            TaxonomicRankEnum.SPECIES,
            TaxonomicRankEnum.GENUS,
            TaxonomicRankEnum.FAMILY,
            TaxonomicRankEnum.ORDER,
        ],
    )

    qField: Optional[QueryFieldEnum] = Field(
        None,
        description="The field to search in. This is an optional parameter that can be used to search in the scientificName or vernacularName field.",
        examples=[QueryFieldEnum.SCIENTIFIC_NAME, QueryFieldEnum.VERNACULAR_NAME],
    )

    # Optional parameters for controlling data retrieval
    includeSynonyms: Optional[bool] = Field(
        True,
        description="Whether to include synonyms in the response. Synonyms are alternative scientific names for the same taxon.",
        examples=[True, False],
    )

    includeChildren: Optional[bool] = Field(
        True,
        description="Whether to include child taxa (subspecies, varieties, etc.) in the response.",
        examples=[True, False],
    )

    includeParents: Optional[bool] = Field(
        True,
        description="Whether to include the complete taxonomic hierarchy (parents) in the response.",
        examples=[True, False],
    )

    language: Optional[str] = Field(
        "en",
        description="Language code for vernacular names and descriptions. Uses ISO 639-1 two-letter codes.",
        examples=["en", "es", "fr", "de", "zh"],
    )

    # Pagination for endpoints that support it
    limit: Optional[int] = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results to return for paginated endpoints (synonyms, children, etc.).",
        examples=[10, 20, 50, 100],
    )

    offset: Optional[int] = Field(
        0,
        ge=0,
        description="Offset for pagination in paginated endpoints.",
        examples=[0, 20, 40],
    )


class GBIFOccurrenceByIdParams(ProductionBaseModel):
    """Parameters for GBIF occurrence by ID - retrieves a single occurrence record by its GBIF ID"""

    gbifId: int = Field(
        ...,
        description="The GBIF ID (gbifId) for the occurrence. This is a required parameter that uniquely identifies the occurrence in the GBIF occurrence store.",
        examples=[1258202889, 5006758998, 4996399785],
    )


class GBIFDatasetSearchParams(ProductionBaseModel):
    """Parameters for GBIF dataset search - full-text search across all datasets with filtering options"""

    # Core search parameters
    q: Optional[str] = Field(
        None,
        description="Simple full text search parameter. The value for this parameter can be a simple word or a phrase. Wildcards are not supported. Only use this parameter if the user's request is vague and none of the other specific parameters are available.",
        examples=["bird observations", "plant specimens", "marine biodiversity"],
    )

    # Dataset type filters
    type: Optional[DatasetTypeEnum] = Field(
        None,
        description="The primary type of the dataset.",
        examples=[
            DatasetTypeEnum.OCCURRENCE,
            DatasetTypeEnum.CHECKLIST,
            DatasetTypeEnum.METADATA,
            DatasetTypeEnum.SAMPLING_EVENT,
        ],
    )

    subtype: Optional[DatasetSubtypeEnum] = Field(
        None,
        description="The sub-type of the dataset.",
        examples=[
            DatasetSubtypeEnum.TAXONOMIC_AUTHORITY,
            DatasetSubtypeEnum.SPECIMEN,
            DatasetSubtypeEnum.OBSERVATION,
        ],
    )

    # Organization filters
    publishingOrg: Optional[str] = Field(
        None,
        description="Filters datasets by their publishing organization UUID key.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"],
    )

    hostingOrg: Optional[str] = Field(
        None,
        description="Filters datasets by their hosting organization UUID key.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"],
    )

    # Content filters
    keyword: Optional[str] = Field(
        None,
        description="Filters datasets by a case insensitive plain text keyword. The search is done on the merged collection of tags, the dataset keywordCollections and temporalCoverages.",
        examples=["biodiversity", "conservation", "taxonomy"],
    )

    decade: Optional[int] = Field(
        None,
        description="Filters datasets by their temporal coverage broken down to decades. Decades are given as a full year, e.g. 1880, 1960, 2000, etc.",
        examples=[1880, 1960, 2000, 2020],
    )

    publishingCountry: Optional[CountryEnum] = Field(
        None,
        description="Filters datasets by their owning organization's country given as a ISO 639-1 (2 letter) country code.",
        examples=[CountryEnum.US, CountryEnum.GB, CountryEnum.DE, CountryEnum.FR],
    )

    hostingCountry: Optional[CountryEnum] = Field(
        None,
        description="Filters datasets by their hosting organization's country given as a ISO 639-1 (2 letter) country code.",
        examples=[CountryEnum.US, CountryEnum.GB, CountryEnum.DE, CountryEnum.FR],
    )

    continent: Optional[ContinentEnum] = Field(
        None,
        description="Filters datasets by continent based on a 7 continent model.",
        examples=[
            ContinentEnum.NORTH_AMERICA,
            ContinentEnum.EUROPE,
            ContinentEnum.ASIA,
        ],
    )

    license: Optional[LicenseEnum] = Field(
        None,
        description="The dataset's licence.",
        examples=[
            LicenseEnum.CC0_1_0,
            LicenseEnum.CC_BY_4_0,
            LicenseEnum.CC_BY_NC_4_0,
        ],
    )

    # Additional filters
    projectId: Optional[str] = Field(
        None,
        description="Filter or facet based on the project ID of a given dataset. A dataset can have a project id if it is the result of a project.",
        examples=["AA003-AA003311F"],
    )

    taxonKey: Optional[int] = Field(
        None,
        description="A taxonKey is the primary id number used in GBIF to id a species (or some higher group). These are the id numbers found in the GBIF backbone taxonomy. Often you will see them in the URL of an occurrence search: https://www.gbif.org/occurrence/search?taxon_key=7412043. These are the most important keys and usually what other keys map back to (rule of thumb: “all keys lead to taxonKeys”).",
        examples=[5231190, 2476674, 2877951],
    )

    recordCount: Optional[str] = Field(
        None,
        description="Number of records of the dataset. Accepts ranges and a `*` can be used as a wildcard.",
        examples=["100,*", "1000,10000", "*"],
    )

    modifiedDate: Optional[str] = Field(
        None,
        description="Date when the dataset was modified the last time. Accepts ranges and a `*` can be used as a wildcard.",
        examples=["2022-05-01,*", "2020,2023", "*"],
    )

    doi: Optional[str] = Field(
        None,
        description="A DOI identifier.",
        examples=["10.15468/dl.abc123"],
    )

    networkKey: Optional[str] = Field(
        None,
        description="Network associated to a dataset.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"],
    )

    endorsingNodeKey: Optional[str] = Field(
        None,
        description="Node key that endorsed this dataset's publisher.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"],
    )

    installationKey: Optional[str] = Field(
        None,
        description="Key of the installation that hosts the dataset.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"],
    )

    endpointType: Optional[EndpointTypeEnum] = Field(
        None,
        description="Type of the endpoint of the dataset.",
        examples=[
            EndpointTypeEnum.DWC_ARCHIVE,
            EndpointTypeEnum.EML,
            EndpointTypeEnum.BIOCASE,
        ],
    )

    category: Optional[str] = Field(
        None,
        description="Category of the dataset.",
        examples=["biodiversity", "taxonomy", "ecology"],
    )

    contactUserId: Optional[str] = Field(
        None,
        description="Filter datasets by contact user ID (e.g., ORCID).",
        examples=["0000-0001-2345-6789"],
    )

    contactEmail: Optional[str] = Field(
        None,
        description="Filter datasets by contact email address.",
        examples=["contact@example.org"],
    )

    # Faceting parameters
    facet: Optional[List[str]] = Field(
        None,
        description="A facet name used to retrieve the most frequent values for a field. This parameter may be repeated to request multiple facets.",
        examples=[
            ["type"],
            ["license", "publishingCountry"],
            ["type", "license", "publishingCountry"],
        ],
    )

    facetMinCount: Optional[int] = Field(
        None,
        ge=1,
        description="Used in combination with the facet parameter. Set to exclude facets with a count less than the specified value.",
        examples=[1, 10, 100],
    )

    facetMultiselect: Optional[bool] = Field(
        None,
        description="Used in combination with the facet parameter. Set to true to still return counts for values that are not currently filtered.",
        examples=[True, False],
    )

    facetLimit: Optional[int] = Field(
        None,
        ge=1,
        max=500,
        description="Facet parameters allow paging requests using the parameters facetOffset and facetLimit.",
        examples=[10, 50, 100],
    )

    facetOffset: Optional[int] = Field(
        None,
        ge=0,
        description="Facet parameters allow paging requests using the parameters facetOffset and facetLimit.",
        examples=[0, 50, 100],
    )

    # Pagination parameters
    limit: Optional[int] = Field(
        20,
        ge=1,
        le=100,
        description="Controls the number of results in the page. Using too high a value will be overwritten with the default maximum threshold.",
        examples=[10, 20, 50, 100],
    )

    offset: Optional[int] = Field(
        0,
        ge=0,
        description="Determines the offset for the search results. A limit of 20 and offset of 40 will get the third page of 20 results.",
        examples=[0, 20, 40],
    )


class GBIFSpeciesNameMatchParams(ProductionBaseModel):
    """
    Fuzzy matches scientific names against the Taxonomy with the optional classification provided. If a classification is provided and strict is not set to true, the default matching will also try to match against these if no direct match is found for the name parameter alone.

    Additionally, a lookup may be performed by providing the usageKey which will short-circuit the name-based matching and ONLY use the given key, either finding the concept or returning no match.
    """

    usageKey: Optional[int] = Field(
        None,
        description="The usage key to look up.",
        examples=[5231190],
    )

    taxonID: Optional[int] = Field(
        None,
        description="The taxon ID to match.",
        examples=[2476674],
    )

    taxonConceptID: Optional[int] = Field(
        None,
        description="The taxon concept ID to match.",
        examples=[2476674],
    )

    scientificNameID: Optional[int] = Field(
        None,
        description="The scientific name ID to match.",
        examples=[2476674],
    )

    scientificName: Optional[str] = Field(
        None,
        description="The scientific name to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    scientificNameAuthorship: Optional[str] = Field(
        None,
        description="The scientific name authorship to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    verbatimTaxonRank: Optional[str] = Field(
        None,
        description="The verbatim taxonomic rank to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    genericName: Optional[str] = Field(
        None,
        description="The generic name to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    specificEpithet: Optional[str] = Field(
        None,
        description="The specific epithet to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    infraspecificEpithet: Optional[str] = Field(
        None,
        description="The infraspecific epithet to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    exclude: Optional[List[int]] = Field(
        None,
        description="The exclude list to match.",
        examples=[2476674],
    )

    strict: Optional[bool] = Field(
        None,
        description="The strict flag to match.",
        examples=[True, False],
    )

    verbose: Optional[bool] = Field(
        None,
        description="The verbose flag to match.",
        examples=[True, False],
    )

    taxonomic_class: Optional[str] = Field(
        None,
        serialization_alias="class",
        description="The class to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    rank: Optional[TaxonomicRankEnum] = Field(
        None,
        description="The rank to match.",
        examples=[
            TaxonomicRankEnum.SPECIES,
            TaxonomicRankEnum.GENUS,
        ],
    )

    kingdom: Optional[str] = Field(
        None,
        description="The kingdom to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    phylum: Optional[str] = Field(
        None,
        description="The phylum to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    order: Optional[str] = Field(
        None,
        description="The order to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    family: Optional[str] = Field(
        None,
        description="The family to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )

    genus: Optional[str] = Field(
        None,
        description="The genus to match.",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )
