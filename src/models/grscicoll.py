"""
GrSciColl API models for institution normalization and matching.
"""

from pydantic import BaseModel, Field, ConfigDict


class AlternativeCode(BaseModel):
    """Alternative code structure from GrSciColl API"""

    model_config = ConfigDict(extra="allow")

    code: str | None = Field(None, description="Alternative code value")
    description: str | None = Field(None, description="Code description")


class GrSciCollInstitutionRecord(BaseModel):
    """A GrSciColl institution record from the API response"""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow extra fields like match_reason, match_id

    key: str | None = Field(None, description="Institution UUID key")
    code: str | None = Field(None, description="Institution code")
    name: str | None = Field(None, description="Institution name")
    alternativeCodes: list[AlternativeCode | str] = Field(
        default_factory=list,
        description="list of alternative codes (can be strings or objects)"
    )
    description: str | None = Field(None, description="Institution description")
    active: bool | None = Field(None, description="Whether the institution is active")
    displayOnNHCPortal: bool | None = Field(
        None, description="Whether to display on NHC portal"
    )
    country: str | None = Field(None, description="Country code (ISO 639-1)")
    mailingCountry: str | None = Field(None, description="Mailing country code")
    mailingCity: str | None = Field(None, description="Mailing city")
    highlights: list[str] = Field(
        default_factory=list, description="Search highlight terms"
    )
    types: list[str] = Field(
        default_factory=list, description="list of institution types"
    )
    institutionalGovernances: list[str] = Field(
        default_factory=list, description="list of institutional governance types"
    )
    disciplines: list[str] = Field(
        default_factory=list, description="list of disciplines"
    )
    occurrenceCount: int | None = Field(
        None, description="Number of occurrences linked to this institution"
    )
    typeSpecimenCount: int | None = Field(
        None, description="Number of type specimens linked to this institution"
    )
