"""
Pydantic models for GBIF Species API responses based on the OpenAPI specification.
"""

from pydantic import BaseModel, Field


class NameUsage(BaseModel):
    """Name usage response from GBIF Species API."""

    # Required fields
    key: int = Field(..., description="The name usage key that uniquely identifies this name usage.")
    datasetKey: str = Field(..., description="The checklist that hosts this name usage.")
    issues: list[str] = Field(..., description="Data quality issues found during processing.")
    origin: str = Field(..., description="The origin of this name usage.")
    scientificName: str = Field(...,
                                description="The scientific name, with date and authorship information if available.")

    # Optional fields
    nubKey: int | None = Field(None, description="The taxon key of the matching backbone name usage.")
    nameKey: int | None = Field(None, description="The key for retrieving a parsed name object.")
    taxonID: str | None = Field(None, description="The original taxonID of the name usage as found in the source.")
    sourceTaxonKey: int | None = Field(None,
                                       description="The key of the name usage from which this backbone taxon derives.")

    # Taxonomic classification
    kingdom: str | None = Field(None, description="Kingdom.")
    phylum: str | None = Field(None, description="Phylum.")
    class_: str | None = Field(None, alias="class", description="Class.")
    order: str | None = Field(None, description="Order.")
    family: str | None = Field(None, description="Family.")
    genus: str | None = Field(None, description="Genus.")
    subgenus: str | None = Field(None, description="Subgenus.")
    species: str | None = Field(None, description="Species.")

    # Taxonomic keys
    kingdomKey: int | None = Field(None, description="Name usage key of the kingdom.")
    phylumKey: int | None = Field(None, description="Name usage key of the phylum.")
    classKey: int | None = Field(None, description="Name usage key of the class.")
    orderKey: int | None = Field(None, description="Name usage key of the order.")
    familyKey: int | None = Field(None, description="Name usage key of the family.")
    genusKey: int | None = Field(None, description="Name usage key of the genus.")
    subgenusKey: int | None = Field(None, description="Name usage key of the subgenus.")
    speciesKey: int | None = Field(None, description="Name usage key of the species.")

    # Additional fields
    constituentKey: str | None = Field(None, description="The optional sub-dataset key for this usage.")
    parentKey: int | None = Field(None, description="The name usage key of the immediate parent.")
    parent: str | None = Field(None, description="The scientific name of the parent.")
    proParteKey: int | None = Field(None, description="The primary name usage key for a pro parte synonym.")
    acceptedKey: int | None = Field(None, description="The name usage key of the accepted name.")
    accepted: str | None = Field(None, description="The scientific name of the accepted name.")
    basionymKey: int | None = Field(None, description="The name usage key of the basionym.")
    basionym: str | None = Field(None, description="The scientific name of the basionym.")
    canonicalName: str | None = Field(None,
                                      description="The canonical name; the name without authorship or references.")
    vernacularName: str | None = Field(None, description="A common or vernacular name for this usage.")
    authorship: str | None = Field(None, description="The authorship for the scientific name.")
    nameType: str | None = Field(None, description="The type of name string classified by Checklistbank.")
    rank: str | None = Field(None, description="The rank for this usage.")
    taxonomicStatus: str | None = Field(None, description="The taxonomic status of this name usage.")
    nomenclaturalStatus: list[str] | None = Field(None, description="The nomenclatural status of this name usage.")
    isExtinct: bool | None = Field(None, description="Whether this taxon is extinct.")
    numDescendants: int | None = Field(None, description="The number of descendant taxa.")
    numOccurrences: int | None = Field(None, description="The number of occurrence records for this taxon.")
    habitat: str | None = Field(None, description="The habitat of this taxon.")
    threatStatus: str | None = Field(None, description="The IUCN threat status of this taxon.")
    description: str | None = Field(None, description="A description of this taxon.")
    accordingTo: str | None = Field(None, description="The source of this information.")
    source: str | None = Field(None, description="The source of this name usage.")
    sourceId: str | None = Field(None, description="The source ID of this name usage.")
    sourceUrl: str | None = Field(None, description="The source URL of this name usage.")
    sourceVersion: str | None = Field(None, description="The source version of this name usage.")
    sourceTitle: str | None = Field(None, description="The source title of this name usage.")
    sourceDescription: str | None = Field(None, description="The source description of this name usage.")
    sourceContact: str | None = Field(None, description="The source contact of this name usage.")
    sourceLogoUrl: str | None = Field(None, description="The source logo URL of this name usage.")
    sourceHomepage: str | None = Field(None, description="The source homepage of this name usage.")
    sourceRights: str | None = Field(None, description="The source rights of this name usage.")
    sourceCitation: str | None = Field(None, description="The source citation of this name usage.")
    sourceDoi: str | None = Field(None, description="The source DOI of this name usage.")
    sourceIdentifier: str | None = Field(None, description="The source identifier of this name usage.")
    sourceModified: str | None = Field(None, description="The source modified date of this name usage.")
    sourceAccessed: str | None = Field(None, description="The source accessed date of this name usage.")
    sourceCreated: str | None = Field(None, description="The source created date of this name usage.")
    sourceUpdated: str | None = Field(None, description="The source updated date of this name usage.")
    sourcePublished: str | None = Field(None, description="The source published date of this name usage.")
    sourceLanguage: str | None = Field(None, description="The source language of this name usage.")
    sourceLicense: str | None = Field(None, description="The source license of this name usage.")
    sourceRightsHolder: str | None = Field(None, description="The source rights holder of this name usage.")
    sourceDatasetKey: str | None = Field(None, description="The source dataset key of this name usage.")
    sourceConstituentKey: str | None = Field(None, description="The source constituent key of this name usage.")
    sourceParentKey: int | None = Field(None, description="The source parent key of this name usage.")
    sourceProParteKey: int | None = Field(None, description="The source pro parte key of this name usage.")
    sourceAcceptedKey: int | None = Field(None, description="The source accepted key of this name usage.")
    sourceBasionymKey: int | None = Field(None, description="The source basionym key of this name usage.")
    sourceScientificName: str | None = Field(None, description="The source scientific name of this name usage.")
    sourceCanonicalName: str | None = Field(None, description="The source canonical name of this name usage.")
    sourceVernacularName: str | None = Field(None, description="The source vernacular name of this name usage.")
    sourceAuthorship: str | None = Field(None, description="The source authorship of this name usage.")
    sourceNameType: str | None = Field(None, description="The source name type of this name usage.")
    sourceRank: str | None = Field(None, description="The source rank of this name usage.")
    sourceTaxonomicStatus: str | None = Field(None, description="The source taxonomic status of this name usage.")
    sourceNomenclaturalStatus: str | None = Field(None,
                                                  description="The source nomenclatural status of this name usage.")
    sourceIsExtinct: bool | None = Field(None, description="The source is extinct flag of this name usage.")
    sourceNumDescendants: int | None = Field(None, description="The source number of descendants of this name usage.")
    sourceNumOccurrences: int | None = Field(None, description="The source number of occurrences of this name usage.")
    sourceHabitat: str | None = Field(None, description="The source habitat of this name usage.")
    sourceThreatStatus: str | None = Field(None, description="The source threat status of this name usage.")
    sourceDescription: str | None = Field(None, description="The source description of this name usage.")
    sourceAccordingTo: str | None = Field(None, description="The source according to of this name usage.")


class PagingResponseNameUsage(BaseModel):
    """Paged response containing NameUsage objects."""

    offset: int = Field(..., description="The offset of the results within all the search results.")
    limit: int = Field(...,
                       description="The limit used. Note the limit returned may be lower than the limit requested.")
    endOfRecords: bool = Field(..., description="True if this page of search results is the final page.")
    count: int | None = Field(None, description="The total number of records returned by the search.")
    results: list[NameUsage] = Field(..., description="Search results.")


SpeciesAPIResponse = NameUsage | PagingResponseNameUsage
