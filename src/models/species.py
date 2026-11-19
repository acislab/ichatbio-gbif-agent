from models.base import ProductionBaseModel
from pydantic import Field
from src.enums.species import (
    NameTypeEnum,
    TaxonomicRankEnum,
    TaxonomicStatusEnum,
    OriginEnum,
    ThreatStatusEnum,
    NomenclaturalStatusEnum,
    IssueEnum,
    HabitatEnum,
    QueryFieldEnum,
)


class SearchFilters(ProductionBaseModel):
    """Full-text search filters for species (q parameter for broad search, qField to narrow to specific fields)."""

    q: str | None = Field(
        None,
        description="Simple full text search parameter covering scientific and vernacular names, species descriptions, distribution and entire classification. The value can be a simple word or phrase. Wildcards are not supported. Results are ordered by relevance. Only use this parameter if the user's request is vague and none of the other specific parameters are available.",
        examples=[
            "Puma concolor",
            "jaguar",
            "Quercus",
            "oak tree",
            "Panthera tigris",
            "endangered cats",
        ]
    )
    qField: QueryFieldEnum | None = Field(
        None,
        description="Use it along with q parameter. Limits the q parameter to search in a specific field. Use it to narrow down the results. Use SCIENTIFIC_NAME when you know or have a good estimate of the scientific name of the species you are searching for. Use VERNACULAR_NAME when you want to find a species using its common name, which can vary by region or language. Use DESCRIPTION when you are looking for a species based on a keyword found in its general description rather than its name.",
    )


class DatasetFilters(ProductionBaseModel):
    """Filters for limiting species searches to specific datasets or checklists."""

    datasetKey: str | None = Field(
        None,
        description="A UUID of a checklist dataset to limit the search scope. Useful for searching within specific taxonomic authorities or regional checklists.",
        examples=["d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"],  # GBIF Backbone Taxonomy
    )

    constituentKey: str | None = Field(
        None,
        description="The (sub)dataset constituent key as a UUID. Useful to query larger assembled datasets such as the GBIF Backbone or the Catalogue of Life for specific constituent parts.",
        examples=["7ce8aef0-9e92-11dc-8738-b8a03c50a862"]
    )


class TaxonomicFilters(ProductionBaseModel):
    """Filters for species by taxonomic rank, higher taxon, or taxonomic status."""

    rank: TaxonomicRankEnum | None = Field(
        None,
        description="Filters by taxonomic rank as defined in the GBIF rank enumeration. Helps narrow results to specific taxonomic levels.",
    )

    higherTaxonKey: int | None = Field(
        None,
        description="Filters by any of the higher Linnean rank keys within the respective checklist. Note this searches within the specific checklist, not across all NUB keys. Useful for finding all taxa under a specific higher taxon.",
        examples=[212, 44, 1448, 2405],  # Example keys for different higher taxa
    )

    status: TaxonomicStatusEnum | None = Field(
        None,
        description="Filters by the taxonomic status to distinguish between accepted names, synonyms, and doubtful names. Essential for taxonomic research and data quality control.",
    )


class NameFilters(ProductionBaseModel):
    """Filters for species by name type, nomenclatural status, and origin."""

    nameType: NameTypeEnum | None = Field(
        None,
        description="Filters by the type of name string as classified by GBIF's name parser. Helps distinguish between different categories of taxonomic names.",
    )

    nomenclaturalStatus: NomenclaturalStatusEnum | None = Field(
        None,
        description="Filters by nomenclatural status according to the relevant nomenclatural code. Important for understanding the validity and legitimacy of scientific names.",
    )

    origin: OriginEnum | None = Field(
        None,
        description="Filters for name usages with a specific origin, indicating how the name usage was created or derived during data processing."
    )


class EcologyFilters(ProductionBaseModel):
    """Filters for species by extinction status, habitat, and conservation threat status."""

    isExtinct: bool | None = Field(
        None,
        description="Filters by extinction status. True returns only extinct taxa, False returns only extant taxa, None returns both."
    )

    habitat: HabitatEnum | None = Field(
        None,
        description="Filters by major habitat classification. Currently supports three major biomes as defined in the GBIF habitat enumeration.",
    )

    threat: ThreatStatusEnum | None = Field(
        None,
        description="Filters by IUCN Red list threat status categories. Useful for conservation research and identifying species of conservation concern."
    )


class QualityFilters(ProductionBaseModel):
    """Filters for species by data quality issues identified during GBIF indexing."""

    issue: IssueEnum | None = Field(
        None,
        description="Filters by specific data quality issues identified during GBIF's indexing process. Useful for data quality assessment and cleanup."
    )
