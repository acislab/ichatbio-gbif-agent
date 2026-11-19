import models
from enums.common import ContinentEnum, LicenseEnum, CountryEnum
from enums.registry import DatasetTypeEnum, DatasetSubtypeEnum, EndpointTypeEnum
from enums.species import TaxonomicRankEnum, QueryFieldEnum
from models.base import ProductionBaseModel
from pydantic import Field


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

    limit: int | None = Field(
        300,
        ge=0,
        le=4800,
        description="The page size (maximum number of records to retrieve). Cannot retrieve more than 4800"
    )

    offset: int | None = Field(
        None,
        ge=0,
        le=100000,
        description="The page offest (how many records to skip)"
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
    limit: int | None = Field(
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
    """Parameters for GBIF species faceting."""

    # Override limit default for faceting (0 for facets only)
    limit: int | None = Field(
        0, ge=0, le=1000, description="Number of results per page (0 for facets only)"
    )


class GBIFSpeciesTaxonomicParams(ProductionBaseModel):
    """Search parameters for GBIF taxonomic records"""

    key: str | None = Field(
        None,
        description="A CoL XR taxon ID",
        examples=["Q2M4", "P", "623RM"]
    )

    name: str | None = Field(
        None,
        description="The scientific name or vernacular name of the taxon",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"]
    )

    rank: TaxonomicRankEnum | None = Field(
        None,
        description="The taxonomic rank of the taxon"
    )

    qField: QueryFieldEnum | None = Field(
        None,
        description="If using the q parameter, this specifies what field to search in, e.g. \"scientificName\" or \"vernacularName\""
    )

    language: str | None = Field(
        "en",
        description="Language code for vernacular names and descriptions. Uses ISO 639-1 two-letter codes.",
        examples=["en", "es", "fr", "de", "zh"]
    )

    # Pagination for endpoints that support it
    limit: int | None = Field(
        20,
        ge=1,
        le=100,
        description="Maximum number of results to return for paginated endpoints (synonyms, children, etc.)."
    )

    offset: int | None = Field(
        0,
        ge=0,
        description="Offset for pagination in paginated endpoints."
    )


class GBIFOccurrenceByIdParams(ProductionBaseModel):
    """Parameters for GBIF occurrence by ID - retrieves a single occurrence record by its GBIF ID"""

    gbifId: str = Field(
        description="The GBIF ID (gbifId) for a single occurrence record. This is a required parameter that uniquely identifies the occurrence in the GBIF occurrence store."
    )


class GBIFDatasetSearchParams(ProductionBaseModel):
    """Parameters for GBIF dataset search - full-text search across all datasets with filtering options"""

    # Core search parameters
    q: str | None = Field(
        None,
        description="Simple full text search parameter. The value for this parameter can be a simple word or a phrase. Wildcards are not supported. Only use this parameter if the user's request is vague and none of the other specific parameters are available.",
        examples=["bird observations", "plant specimens", "marine biodiversity"]
    )

    # Dataset type filters
    type: DatasetTypeEnum | None = Field(
        None,
        description="The primary type of the dataset."
    )

    subtype: DatasetSubtypeEnum | None = Field(
        None,
        description="The sub-type of the dataset."
    )

    # Organization filters
    publishingOrg: str | None = Field(
        None,
        description="Filters datasets by their publishing organization UUID key.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"]
    )

    hostingOrg: str | None = Field(
        None,
        description="Filters datasets by their hosting organization UUID key.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"]
    )

    # Content filters
    keyword: str | None = Field(
        None,
        description="Filters datasets by a case insensitive plain text keyword. The search is done on the merged collection of tags, the dataset keywordCollections and temporalCoverages.",
        examples=["biodiversity", "conservation", "taxonomy"]
    )

    decade: int | None = Field(
        None,
        description="Filters datasets by their temporal coverage broken down to decades. Decades are given as a full year, e.g. 1880, 1960, 2000, etc."
    )

    publishingCountry: CountryEnum | None = Field(
        None,
        description="Filters datasets by their owning organization's country given as a ISO 639-1 (2 letter) country code."
    )

    hostingCountry: CountryEnum | None = Field(
        None,
        description="Filters datasets by their hosting organization's country given as a ISO 639-1 (2 letter) country code."
    )

    continent: ContinentEnum | None = Field(
        None,
        description="Filters datasets by continent based on a 7 continent model."
    )

    license: LicenseEnum | None = Field(
        None,
        description="The dataset's licence."
    )

    # Additional filters
    projectId: str | None = Field(
        None,
        description="Filter or facet based on the project ID of a given dataset. A dataset can have a project id if it is the result of a project.",
        examples=["AA003-AA003311F"]
    )

    taxonKey: str | None = Field(
        None,
        description="A taxonKey is the primary id number used in GBIF to id a species (or some higher group). These are the id numbers found in the GBIF backbone taxonomy. Often you will see them in the URL of an occurrence search: https://www.gbif.org/occurrence/search?taxon_key=7412043. These are the most important keys and usually what other keys map back to (rule of thumb: “all keys lead to taxonKeys”).",
        examples=[5231190, 2476674, 2877951]
    )

    recordCount: str | None = Field(
        None,
        description="Number of records of the dataset. Accepts ranges and a `*` can be used as a wildcard.",
        examples=["100,*", "1000,10000", "*"]
    )

    modifiedDate: str | None = Field(
        None,
        description="Date when the dataset was modified the last time. Accepts ranges and a `*` can be used as a wildcard.",
        examples=["2022-05-01,*", "2020,2023", "*"]
    )

    doi: str | None = Field(
        None,
        description="A DOI identifier."
    )

    networkKey: str | None = Field(
        None,
        description="Network associated to a dataset.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"]
    )

    endorsingNodeKey: str | None = Field(
        None,
        description="Node key that endorsed this dataset's publisher.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"]
    )

    installationKey: str | None = Field(
        None,
        description="Key of the installation that hosts the dataset.",
        examples=["b542788f-0dc2-4a2b-b652-fceced449591"]
    )

    endpointType: EndpointTypeEnum | None = Field(
        None,
        description="Type of the endpoint of the dataset."
    )

    category: str | None = Field(
        None,
        description="Category of the dataset.",
        examples=["biodiversity", "taxonomy", "ecology"]
    )

    contactUserId: str | None = Field(
        None,
        description="Filter datasets by contact user ID (e.g., ORCID).",
        examples=["0000-0001-2345-6789"]
    )

    contactEmail: str | None = Field(
        None,
        description="Filter datasets by contact email address."
    )

    # Faceting parameters
    facet: list[str] | None = Field(
        None,
        description="A facet name used to retrieve the most frequent values for a field. This parameter may be repeated to request multiple facets.",
        examples=[
            ["type"],
            ["license", "publishingCountry"],
            ["type", "license", "publishingCountry"],
        ]
    )

    facetMinCount: int | None = Field(
        None,
        ge=1,
        description="Used in combination with the facet parameter. Set to exclude facets with a count less than the specified value."
    )

    facetMultiselect: bool | None = Field(
        None,
        description="Used in combination with the facet parameter. Set to true to still return counts for values that are not currently filtered."
    )

    facetLimit: int | None = Field(
        None,
        ge=1,
        max=500,
        description="Facet parameters allow paging requests using the parameters facetOffset and facetLimit."
    )

    facetOffset: int | None = Field(
        None,
        ge=0,
        description="Facet parameters allow paging requests using the parameters facetOffset and facetLimit."
    )

    # Pagination parameters
    limit: int | None = Field(
        20,
        ge=1,
        le=100,
        description="Controls the number of results in the page. Using too high a value will be overwritten with the default maximum threshold."
    )

    offset: int | None = Field(
        0,
        ge=0,
        description="Determines the offset for the search results. A limit of 20 and offset of 40 will get the third page of 20 results."
    )


class GBIFSpeciesNameMatchParams(ProductionBaseModel):
    """
    Fuzzy matches scientific names against the Taxonomy with the optional classification provided. If a classification is provided and strict is not set to true, the default matching will also try to match against these if no direct match is found for the name parameter alone.

    Additionally, a lookup may be performed by providing the usageKey which will short-circuit the name-based matching and ONLY use the given key, either finding the concept or returning no match.
    """

    usageKey: str | None = Field(
        None,
        description="A CoL XR taxon key. When provided, all other fields are ignored.",
        examples=["N", "3PQ6", "8VRHY"]
    )

    taxonID: str | None = Field(
        None,
        description="The taxonID to match. Matches to a taxonID will take precedence over scientificName values supplied. A comparison of the matched scientific and taxonID is performed to check for inconsistencies. See Darwin core term http://rs.tdwg.org/dwc/terms/taxonID for more details.",
        examples=["8fa58e08-08de-4ac1-b69c-1235340b7001", "32567", "https://www.gbif.org/species/212"]
    )

    taxonConceptID: str | None = Field(
        None,
        description="The taxonConceptID to match. Matches to a taxonConceptID will take precedence over scientificName values supplied. A comparison of the matched scientific and taxonConceptID is performed to check for inconsistencies. See Darwin core term http://rs.tdwg.org/dwc/terms/taxonConceptID for more details.",
        examples=["8fa58e08-08de-4ac1-b69c-1235340b7001"]
    )

    scientificNameID: int | None = Field(
        None,
        description="The scientificNameID to match. Matches to a scientificNameID will take precedence over scientificName values supplied. A comparison of the matched scientific and scientificNameID is performed to check for inconsistencies. See Darwin core term http://rs.tdwg.org/dwc/terms/scientificNameID for more details",
        examples=["urn:lsid:ipni.org:names:37829-1:1.3"]
    )

    scientificName: str | None = Field(
        None,
        description="The scientific name to fuzzy match against. May include the authorship and year",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"]
    )

    scientificNameAuthorship: str | None = Field(
        None,
        description="The authorship information for the dwc:scientificName formatted according to the conventions of the applicable dwc:nomenclaturalCode",
        examples=["(Torr.) J.T. Howell", "(Martinovský) Tzvelev", "(Györfi, 1952)"]
    )

    taxonRank: str | None = Field(
        None,
        description="The taxonomic rank of the most specific name in the dwc:scientificName",
        examples=["subspecies", "varietas", "forma", "species", "genus", "nothogenus", "nothospecies",
                  "nothosubspecies"]
    )

    verbatimTaxonRank: str | None = Field(
        None,
        description="The taxonomic rank of the most specific name in the dwc:scientificName as it appears in the original record.",
        examples=["Agamospecies", "sub-lesus", "prole", "apomict", "nothogrex", "sp.", "subsp.", "var."]
    )

    genericName: str | None = Field(
        None,
        description="Generic part of the name to match when given as atomised parts instead of the full name parameter",
        examples=["Abacetus (Parastygis)", "Dicranum subgen. Orthodicranum"]
    )

    specificEpithet: str | None = Field(
        None,
        description="The second word in a binomial scientific name",
        examples=["onca", "robur"]
    )

    infraspecificEpithet: str | None = Field(
        None,
        description="The name of the lowest or terminal infraspecific of a scientific name",
        examples=["concolor (for scientificName Puma concolor concolor)",
                  "oxyadenia (for scientificName Quercus agrifolia var. oxyadenia)",
                  "laxa (for scientificName Cheilanthes hirta f. laxa)",
                  "scaberrima (for scientificName Indigofera charlieriana var. scaberrima)"]
    )

    kingdom: str | None = Field(
        None,
        examples=["Animalia", "Archaea", "Bacteria", "Chromista", "Fungi", "Plantae", "Protozoa", "Viruses"]
    )

    phylum: str | None = Field(
        None,
        examples=["Chordata", "Bryophyta"]
    )

    order: str | None = Field(
        None,
        examples=["Carnivora", "Monocleales"]
    )

    superfamily: str | None = Field(
        None,
        examples=["Achatinoidea", "Cerithioidea", "Helicoidea", "Hypsibioidea", "Valvatoidea", "Zonitoidea"]
    )

    family: str | None = Field(
        None,
        examples=["Felidae", "Monocleaceae"]
    )

    subfamily: str | None = Field(
        None,
        examples=["Periptyctinae", "Orchidoideae", "Sphindociinae"]
    )

    tribe: str | None = Field(
        None,
        examples=["Ortaliini", "Arethuseae"]
    )

    subtribe: str | None = Field(
        None,
        examples=["Plotinini", "Typhaeini"]
    )

    genus: str | None = Field(
        None,
        examples=["Panthera", "Quercus"]
    )

    subgenus: str | None = Field(
        None,
        examples=["Abacetus (Parastygis)", "Dicranum subgen. Orthodicranum"]
    )

    species: str | None = Field(
        None
    )

    exclude: list[str] | None = Field(
        None,
        description="An array of usage keys to exclude from the match"
    )

    strict: bool | None = Field(
        None,
        description="If set to true, fuzzy matches only the given name, but never a taxon in the upper classification"
    )

    verbose: bool | None = Field(
        None,
        description="If set to true, it shows alternative matches which were considered but then rejected"
    )
