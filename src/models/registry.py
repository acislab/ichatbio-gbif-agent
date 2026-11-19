"""
Registry Parameters Models

This module contains parameter models for registry-related API endpoints based on the GBIF OpenAPI specification.
"""

from uuid import UUID

from models.common import PaginationParams
from pydantic import Field
from src.enums.common import CountryEnum, GbifRegionEnum
from src.enums.registry import (
    MasterSourceTypeEnum,
    MasterSourceEnum,
    IdentifierTypeEnum,
    SortByEnum,
    SortOrderEnum,
)


class GBIFGrSciCollInstitutionSearchParams(PaginationParams):
    """
    Parameters for GBIF GrSciColl institution search endpoint (/grscicoll/institution/search).
    
    This endpoint searches for institutions in the Global Registry of Scientific Collections (GRSciColl).
    """

    # Full text search
    q: str | None = Field(
        None,
        description="Simple full text search parameter. The value for this parameter can be a simple word or a phrase. Wildcards are not supported",
        examples=["Smithsonian", "Natural History Museum", "botanical"]
    )

    hl: bool | None = Field(
        None,
        description="Set `hl=true` to highlight terms matching the query when in fulltext search fields. The highlight will be an emphasis tag of class `gbifHl`"
    )

    fuzzyName: str | None = Field(
        None,
        description="It searches by name fuzzily so the parameter doesn't have to be the exact name",
        examples=["Smithsonian", "Natural History"]
    )

    # Institution identifiers
    code: str | None = Field(
        None,
        description="Code of a GrSciColl institution or collection",
        examples=["USNM", "NHM"]
    )

    name: str | None = Field(
        None,
        description="Name of a GrSciColl institution or collection",
        examples=["Smithsonian Institution", "Natural History Museum"]
    )

    alternativeCode: str | None = Field(
        None,
        description="Alternative code of a GrSciColl institution or collection"
    )

    # Institution classification
    type: list[str] | None = Field(
        None,
        description="Type of a GrSciColl institution. Accepts multiple values, for example `type=Museum&type=BotanicalGarden`",
        examples=[["Museum", "BotanicalGarden"]]
    )

    institutionalGovernance: list[str] | None = Field(
        None,
        description="Institutional governance of a GrSciColl institution. Accepts multiple values, for example `InstitutionalGovernance=NonProfit&InstitutionalGovernance=Local`",
        examples=[["NonProfit", "Local"]]
    )

    discipline: list[str] | None = Field(
        None,
        description="Discipline of a GrSciColl institution. Accepts multiple values, for example `discipline=Zoology&discipline=Biological`",
        examples=[["Zoology", "Biological"]]
    )

    # Master source metadata
    sourceId: str | None = Field(
        None,
        description="sourceId of MasterSourceMetadata"
    )

    source: MasterSourceEnum | None = Field(
        None,
        description="Source attribute of MasterSourceMetadata"
    )

    masterSourceType: MasterSourceTypeEnum | None = Field(
        None,
        description="The master source type of a GRSciColl institution or collection"
    )

    # Identifiers
    identifierType: IdentifierTypeEnum | None = Field(
        None,
        description="An identifier type for the identifier parameter"
    )

    identifier: str | None = Field(
        None,
        description="An identifier of the type given by the identifierType parameter, for example a DOI or UUID",
        examples=["10.1234/example", "fa252605-26f6-426c-9892-94d071c2c77f"]
    )

    # Location filters
    country: list[CountryEnum] | None = Field(
        None,
        description="Filters by country given as a ISO 639-1 (2 letter) country code"
    )

    gbifRegion: list[GbifRegionEnum] | None = Field(
        None,
        description="Filters by a gbif region"
    )

    city: str | None = Field(
        None,
        description="Filters by the city of the address. It searches in both the physical and the mailing address",
        examples=["Washington", "London", "Paris"]
    )

    # Contact filters
    contact: UUID | None = Field(
        None,
        description="Filters collections and institutions whose contacts contain the person key specified",
        examples=["fa252605-26f6-426c-9892-94d071c2c77f"]
    )

    contactUserId: str | None = Field(
        None,
        description="Filter by contact user ID"
    )

    contactEmail: str | None = Field(
        None,
        description="Filter by contact email"
    )

    # Machine tags
    machineTagNamespace: str | None = Field(
        None,
        description="Filters for entities with a machine tag in the specified namespace"
    )

    machineTagName: str | None = Field(
        None,
        description="Filters for entities with a machine tag with the specified name (use in combination with the machineTagNamespace parameter)"
    )

    machineTagValue: str | None = Field(
        None,
        description="Filters for entities with a machine tag with the specified value (use in combination with the machineTagNamespace and machineTagName parameters)"
    )

    # Status and display
    active: bool | None = Field(
        None,
        description="Active status of a GrSciColl institution or collection"
    )

    displayOnNHCPortal: bool | None = Field(
        None,
        description="Flag to show this record in the NHC portal"
    )

    # Counts and ranges (string format to support ranges and wildcards)
    numberSpecimens: str | None = Field(
        None,
        description="Number of specimens. It supports ranges and a `*` can be used as a wildcard",
        examples=["1000-5000", "10000*"]
    )

    occurrenceCount: str | None = Field(
        None,
        description="Count of occurrences linked. It supports ranges and a `*` can be used as a wildcard",
        examples=["1000-5000", "10000*"]
    )

    typeSpecimenCount: str | None = Field(
        None,
        description="Count of type specimens linked. It supports ranges and a `*` can be used as a wildcard",
        examples=["100-500", "1000*"]
    )

    # Relationships
    institutionKey: list[UUID] | None = Field(
        None,
        description="Keys of institutions to filter by",
        examples=[[UUID("fa252605-26f6-426c-9892-94d071c2c77f")]]
    )

    replacedBy: UUID | None = Field(
        None,
        description="Key of the entity that replaced another entity",
        examples=[UUID("fa252605-26f6-426c-9892-94d071c2c77f")]
    )

    # Sorting
    sortBy: SortByEnum | None = Field(
        None,
        description="Field to sort the results by. It only supports the fields contained in the enum"
    )

    sortOrder: SortOrderEnum | None = Field(
        None,
        description="Sort order to use with the sortBy parameter"
    )
