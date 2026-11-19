from models.base import ProductionBaseModel
from pydantic import Field


class PaginationParams(ProductionBaseModel):
    """Pagination controls for search results (limit, offset, or page-based navigation)."""

    limit: int | None = Field(
        20,
        ge=0,
        le=1000,
        description="Controls the number of results in the page. Using too high a value will be overwritten with the maximum threshold. Default varies by service (20 for species, 100 for occurrences)."
    )

    offset: int | None = Field(
        0,
        ge=0,
        description="Determines the offset for the search results. A limit of 20 and offset of 40 will get the third page of 20 results. Some services have a maximum offset (e.g., 100,000 for occurrences)."
    )

    page: int | None = Field(
        None,
        ge=1,
        description="Page number for pagination (alternative to offset). Use with limit for pagination. For example, limit=20 and page=3 returns the third page of 20 results. Available for species searches."
    )


class FacetParams(ProductionBaseModel):
    """Faceting parameters for retrieving frequency counts and statistical breakdowns of search results."""

    facet: list[str] | None = Field(
        default=None,
        description="A facet name used to retrieve the most frequent values for a field. This parameter may be repeated to request multiple facets. Note: terms not available for searching are not available for faceting. If omitted, only the total count is returned without breakdowns. For occurrences: facets are allowed for all search parameters except geometry and geoDistance.",
        examples=[
            ["scientificName"],
            ["country", "year"],
            ["basisOfRecord", "kingdom"],
            ["datasetKey", "publishingCountry"],
            ["rank"],
            ["status", "habitat"],
            ["nameType", "threat"],
        ]
    )

    facetLimit: int | None = Field(
        100,
        ge=1,
        description="Used in combination with the facet parameter. Maximum number of facet values to return per facet field. Set facetLimit={#} to limit the number of facets returned."
    )

    facetOffset: int | None = Field(
        0,
        ge=0,
        description="Used in combination with the facet parameter. Starting offset for facet value results. Set facetOffset={#} to offset the number of facets returned. Use with facetLimit for paginating through facet values when there are many distinct values."
    )

    facetMincount: int | None = Field(
        1,
        ge=1,
        description="Used in combination with the facet parameter. Minimum count threshold for facet values. Set facetMincount={#} to exclude facets with a count less than {#}. Excludes facet values with counts below this threshold to reduce noise in facet results."
    )

    facetMultiselect: bool | None = Field(
        False,
        description="Used in combination with the facet parameter. When enabled, facet counts include values that are not currently filtered. Set facetMultiselect=true to still return counts for values that are not currently filtered, allowing for multi-select filter interfaces with accurate counts."
    )
