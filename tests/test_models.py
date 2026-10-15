import pytest
from pydantic import ValidationError

from enums.occurrences import BasisOfRecordEnum
from src.models.entrypoints import (
    GBIFOccurrenceSearchParams,
    GBIFOccurrenceFacetsParams
)


def test_valid_basic_params():
    # Test creation with basic valid parameters
    params = GBIFOccurrenceSearchParams(
        scientificName=["Quercus robur"],
        basisOfRecord=[BasisOfRecordEnum.PRESERVED_SPECIMEN],
    )
    assert params.limit == 300  # default value if not set
    assert params.scientificName == ["Quercus robur"]


def test_valid_facets_configuration():
    # Test creation with valid facet parameters
    params = GBIFOccurrenceFacetsParams(
        facet=["scientificName", "country"],
        facetMincount=10,
        scientificName=["Puma concolor"],
    )
    assert params.limit == 0  # facet model override
    assert params.facetMincount == 10


@pytest.mark.skip("Is facet no longer required?") # TODO
def test_required_facet_parameter():
    # Test that facet parameter is required
    with pytest.raises(ValidationError) as exc_info:
        GBIFOccurrenceFacetsParams()
    assert "facet" in str(exc_info.value).lower()
