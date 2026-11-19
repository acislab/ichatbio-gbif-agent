"""
Bionomia API models for name normalization and matching.
"""
from typing import TypedDict

from pydantic import BaseModel, Field, ConfigDict


class BionomiaNameRecord(BaseModel):
    """A Bionomia name record from the API response"""

    model_config = ConfigDict(
        extra="allow"
    )  # Allow extra fields like match_reason, match_id

    id: str | None = Field(None, description="Bionomia user ID")
    score: float | None = Field(None, description="API similarity score")
    orcid: str | None = Field(None, description="ORCID identifier")
    wikidata: str | None = Field(None, description="Wikidata identifier (e.g., 'Q113489547')")
    uri: str | None = Field(None, description="URI to the person's record")
    fullname: str | None = Field(None, description="Full name of the person")
    fullname_reverse: str | None = Field(None, description="Full name in reverse format (Last, First)")
    given: str | None = Field(None, description="Given name")
    family: str | None = Field(None, description="Family name")
    label: str | None = Field(None, description="Preferred label/display name")
    other_names: list[str] = Field(default_factory=list, description="list of alternative names")
    thumbnail: str | None = Field(None, description="Thumbnail image URL")
    lifespan: str | None = Field(None, description="Lifespan dates if known")
    description: str | None = Field(None, description="Description of the person")
    is_public: bool | None = Field(None, description="Whether the record is public")
    has_occurrences: bool | None = Field(None, description="Whether the person has occurrence records")


class NameMatchResult(TypedDict, total=False):
    """Result structure from find_best_name_match"""
    monologue: str
    matches: list[dict]  # list of BionomiaNameRecord dicts with match_reason and match_confidence


class BionomiaErrorResult(TypedDict):
    """Error result structure from normalize_name"""
    status: str
    original: str
    found_count: int | None
    threshold: float | None
    error: str | None
    fallback: dict | None
