"""
GrSciColl API models for institution normalization and matching.
"""
from typing import Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class AlternativeCode(BaseModel):
    """Alternative code structure from GrSciColl API"""

    model_config = ConfigDict(extra="allow")

    code: Optional[str] = Field(None, description="Alternative code value")
    description: Optional[str] = Field(None, description="Code description")


class GrSciCollInstitutionRecord(BaseModel):
    """A GrSciColl institution record from the API response"""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow extra fields like match_reason, match_id

    key: Optional[str] = Field(None, description="Institution UUID key")
    code: Optional[str] = Field(None, description="Institution code")
    name: Optional[str] = Field(None, description="Institution name")
    alternativeCodes: list[Union[AlternativeCode, str]] = Field(
        default_factory=list,
        description="List of alternative codes (can be strings or objects)",
    )
    description: Optional[str] = Field(None, description="Institution description")
    active: Optional[bool] = Field(None, description="Whether the institution is active")
    displayOnNHCPortal: Optional[bool] = Field(
        None, description="Whether to display on NHC portal"
    )
    country: Optional[str] = Field(None, description="Country code (ISO 639-1)")
    mailingCountry: Optional[str] = Field(None, description="Mailing country code")
    mailingCity: Optional[str] = Field(None, description="Mailing city")
    highlights: list[str] = Field(
        default_factory=list, description="Search highlight terms"
    )
    types: list[str] = Field(
        default_factory=list, description="List of institution types"
    )
    institutionalGovernances: list[str] = Field(
        default_factory=list, description="List of institutional governance types"
    )
    disciplines: list[str] = Field(
        default_factory=list, description="List of disciplines"
    )
    occurrenceCount: Optional[int] = Field(
        None, description="Number of occurrences linked to this institution"
    )
    typeSpecimenCount: Optional[int] = Field(
        None, description="Number of type specimens linked to this institution"
    )
