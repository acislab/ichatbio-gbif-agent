from typing import Tuple

from pydantic import BaseModel, Field
from src.enums.common import CountryEnum
from util_types import ParameterEnum


class Location(BaseModel):
    """
    Hierarchical geographic address.

    Used by:
    - LLM to extract locations from user requests
    - GADM module to resolve locations to GADM IDs
    - GBIF API to filter by geographic location

    Examples:
        Location(country="USA", state="Florida", county="Alachua")
        Location(country="India", state="Karnataka")
        Location(country="USA", state="California", locality="San Francisco")
    """

    continent: str | None = Field(
        None, description="Continent name (e.g., 'North America', 'Asia', 'Europe')"
    )
    country: str | None = Field(
        None, description="Country name (e.g., 'United States', 'India', 'Brazil')"
    )
    country_iso: CountryEnum | None = Field(
        None,
        description="ISO 3166-1 alpha-2 country code (e.g., 'US', 'IN', 'BR')"
    )
    state: str | None = Field(
        None,
        description="State/province name (e.g., 'California', 'Karnataka', 'Ontario')"
    )
    state_iso: str | None = Field(
        None, description="State/province code if applicable (e.g., 'CA', 'FL', 'NY')"
    )
    county: str | None = Field(
        None, description="County/district name (e.g., 'Alachua', 'Pauri', 'King')"
    )
    locality: str | None = Field(
        None,
        description="City/town/locality name (e.g., 'Gainesville', 'Mumbai', 'Montreal')"
    )
    protected_area: str | None = Field(
        None,
        description="Protected area name (e.g., 'Yellowstone', 'Kruger', 'Serengeti')"
    )

    # ========================================================================
    # PROPERTIES - Used by GADM resolution
    # ========================================================================

    @property
    def most_specific(self) -> Tuple[str | None, str | None]:
        """
        Return (level, name) of most specific location.

        Returns:
            Tuple of (level_name, place_name) or (None, None) if empty

        Example:
            >>> loc = Location(country="USA", state="Florida", county="Alachua")
            >>> loc.most_specific
            ('county', 'Alachua')
        """
        if self.locality:
            return ("locality", self.locality)
        if self.county:
            return ("county", self.county)
        if self.state:
            return ("state", self.state)
        if self.country:
            return ("country", self.country)
        if self.continent:
            return ("continent", self.continent)
        return (None, None)

    @property
    def hierarchy_list(self) -> list[Tuple[str, str]]:
        """
        Return list of (level, name) from least to most specific.

        Returns:
            list of tuples: [(level_name, place_name), ...]

        Example:
            >>> loc = Location(country="USA", state="Florida", county="Alachua")
            >>> loc.hierarchy_list
            [('country', 'USA'), ('state', 'Florida'), ('county', 'Alachua')]
        """
        result = []
        if self.continent:
            result.append(("continent", self.continent))
        if self.country:
            result.append(("country", self.country))
        if self.state:
            result.append(("state", self.state))
        if self.county:
            result.append(("county", self.county))
        if self.locality:
            result.append(("locality", self.locality))
        if self.protected_area:
            result.append(("protected_area", self.protected_area))
        return result

    def get_hierarchy(self) -> list[Tuple[int, str, str]]:
        """
        Get location hierarchy as list of (gadm_level, level_name, place_name).

        Used by GADM resolution module.

        Returns:
            list from most specific to least specific:
            [(3, 'locality', 'Gainesville'), (2, 'county', 'Alachua'), (1, 'state', 'Florida'), (0, 'country', 'USA')]

        Example:
            >>> loc = Location(country="USA", state="Florida", county="Alachua", locality="Gainesville")
            >>> loc.get_hierarchy()
            [(3, 'locality', 'Gainesville'), (2, 'county', 'Alachua'), (1, 'state', 'Florida'), (0, 'country', 'USA')]
        """
        hierarchy = []

        # Map location fields to GADM levels
        # GADM levels: 0=country, 1=state/province, 2=county/district, 3=locality

        if self.locality:
            hierarchy.append((3, "locality", self.locality))

        if self.county:
            hierarchy.append((2, "county", self.county))

        if self.state:
            hierarchy.append((1, "state", self.state))

        if self.country:
            hierarchy.append((0, "country", self.country))

        return hierarchy

    def get_parent_constraints(self, for_level: int) -> dict[int, str]:
        """
        Get parent location names for disambiguating at a given level.

        Used by GADM resolution to constrain searches.

        Args:
            for_level: GADM level to get parents for

        Returns:
            dict mapping parent levels to names

        Example:
            >>> loc = Location(country="USA", state="Florida", county="Alachua")
            >>> loc.get_parent_constraints(for_level=2)
            {1: 'Florida', 0: 'USA'}

            This means: when searching for county (level 2), constrain by
            state=Florida (level 1) and country=USA (level 0)
        """
        constraints = {}
        hierarchy = self.get_hierarchy()

        for level, _, name in hierarchy:
            if level < for_level:  # Only include parents (lower levels)
                constraints[level] = name

        return constraints

    def is_empty(self) -> bool:
        """Check if location has any data"""
        return not any(
            [
                self.continent,
                self.country,
                self.state,
                self.county,
                self.locality,
                self.protected_area,
            ]
        )

    def __str__(self) -> str:
        """Human-readable string representation"""
        parts = []
        if self.locality:
            parts.append(self.locality)
        if self.county:
            parts.append(self.county)
        if self.protected_area:
            parts.append(self.protected_area)
        if self.state:
            parts.append(self.state)
        if self.country:
            parts.append(self.country)
        if self.continent:
            parts.append(self.continent)
        return ", ".join(parts) if parts else "Empty Location"


class GadmMatchType(ParameterEnum):
    """
    Amount of location information that was found in GADM
    """

    COMPLETE = "complete"
    PARTIAL = "partial"
    NONE = "none"


class GADMHierarchyLevel(BaseModel):
    """Represents a single level in the GADM administrative hierarchy."""

    name: str | None = Field(
        default=None, description="Administrative division name at this level"
    )
    gid: str | None = Field(
        default=None, description="GADM identifier at this level"
    )


class GADMHierarchy(BaseModel):
    """Complete GADM administrative hierarchy."""

    level_0: GADMHierarchyLevel | None = Field(
        default=None, description="Country level"
    )
    level_1: GADMHierarchyLevel | None = Field(
        default=None, description="First administrative division (state/province)"
    )
    level_2: GADMHierarchyLevel | None = Field(
        default=None, description="Second administrative division (county/district)"
    )
    level_3: GADMHierarchyLevel | None = Field(
        default=None, description="Third administrative division"
    )


class GADMMatch(BaseModel):
    """
    Location information that was found in GADM
    """

    match_type: GadmMatchType = Field(
        default=GadmMatchType.NONE,
        description="Amount of location information that was found in GADM"
    )
    gadm_hierarchy: GADMHierarchy | None = Field(
        default=None,
        description="Hierarchy of location information that was found in GADM"
    )
    query_trace: list[str] | None = Field(
        default=None,
        description="Trace of queries made to GADM"
    )


class ResolvedLocation(Location, GADMMatch):
    """Location merged with GADM resolution - all fields flattened."""

    pass


class EnrichedLocation(BaseModel):
    """Location enriched with GADM validation and hierarchy data."""

    # Original LLM extraction
    original_location: Location = Field(description="Original location from LLM")

    # GADM enrichment
    was_found_in_gadm: bool = Field(
        default=False,
        description="True if location was found and validated in GADM database"
    )
    gadm_gid: str | None = Field(
        default=None, description="GADM ID (e.g., 'USA.11.1_1')"
    )
    gadm_level: int | None = Field(
        default=None,
        description="Administrative level in GADM (0=country, 1=state, etc.)"
    )
    gadm_canonical_name: str | None = Field(
        default=None, description="Canonical name from GADM"
    )
    gadm_hierarchy: GADMHierarchy | None = Field(
        default=None, description="Complete administrative hierarchy from GADM"
    )
    resolution_trace: list | None = Field(
        default=None, description="SQL queries executed during GADM resolution"
    )
    validation_note: str | None = Field(
        default=None,
        description="Notes about validation process (e.g., 'exact match', 'not found')"
    )
