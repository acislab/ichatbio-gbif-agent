import pytest

from src.gbif.api import GbifApi
from src.gbif.fetch import execute_sync_request
from src.models.entrypoints import GBIFOccurrenceSearchParams, GBIFOccurrenceFacetsParams
from src.models.occurrences import (
    BasisOfRecordEnum,
    ContinentEnum,
    OccurrenceStatusEnum,
    LicenseEnum,
    MediaObjectTypeEnum,
)


@pytest.fixture
def url_builder():
    return GbifApi()


@pytest.fixture
def fetcher():
    return execute_sync_request()


def test_api_initialization(url_builder):
    assert url_builder.base_url == "https://api.gbif.org"
    assert url_builder.portal_url == "https://gbif.org"


def test_convert_to_api_params(url_builder):
    basic_params = GBIFOccurrenceSearchParams(  # type: ignore
        q="Quercus robur",
        scientificName=["Quercus robur"],
        limit=10
    )
    basic_result = url_builder._convert_to_api_params(basic_params)
    assert basic_result["q"] == "Quercus robur"
    assert basic_result["scientificName"] == ["Quercus robur"]
    assert basic_result["limit"] == 10
    assert "offset" not in basic_result

    enum_params = GBIFOccurrenceSearchParams(  # type: ignore
        basisOfRecord=[BasisOfRecordEnum.PRESERVED_SPECIMEN],
        continent=[ContinentEnum.EUROPE],
        occurrenceStatus=OccurrenceStatusEnum.PRESENT,
        license=[LicenseEnum.CC0_1_0],
        mediaType=[MediaObjectTypeEnum.StillImage]
    )
    enum_result = url_builder._convert_to_api_params(enum_params)
    assert enum_result["basisOfRecord"] == ["PRESERVED_SPECIMEN"]
    assert enum_result["continent"] == ["EUROPE"]
    assert enum_result["occurrenceStatus"] == "PRESENT"
    assert enum_result["license"] == ["CC0_1_0"]
    assert enum_result["mediaType"] == ["StillImage"]


def test_url_building(url_builder):
    """Test URL building for different endpoints."""
    # Test search URL
    search_params = GBIFOccurrenceSearchParams(  # type: ignore
        scientificName=["Quercus robur"], limit=5, offset=10
    )
    search_url = url_builder.build_occurrence_search_url(search_params)
    assert search_url.startswith("https://api.gbif.org/v1/occurrence/search?")
    assert "scientificName=Quercus+robur" in search_url
    assert "limit=5" in search_url
    assert "offset=10" in search_url

    # Test facets URL
    facets_params = GBIFOccurrenceFacetsParams(  # type: ignore
        facet=["kingdom", "country"], facetMincount=5
    )
    facets_url = url_builder.build_occurrence_facets_url(facets_params)
    assert facets_url.startswith("https://api.gbif.org/v1/occurrence/search?")
    assert "facet=country" in facets_url
    assert "facetMincount=5" in facets_url


class TestBuildPortalURLs:
    def test_occurrence_search(self, url_builder):
        params = GBIFOccurrenceSearchParams(scientificName=["Quercus robur"], limit=5, offset=10)
        portal_url = url_builder.build_portal_url("occurrence/search", params)
        assert portal_url == "https://gbif.org/occurrence/search?offset=10&scientificName=Quercus robur"

    def test_remove_facet_parameters(self, url_builder):
        params = GBIFOccurrenceFacetsParams(country=["MN"], facet=["kingdom", "country"], facetMincount=5)
        portal_url = url_builder.build_portal_url("occurrence/search", params)
        assert portal_url == "https://gbif.org/occurrence/search?country=MN"

    def test_build_portal_url_with_repeated_parameters(self, url_builder):
        params = GBIFOccurrenceSearchParams(recordedBy=["Fred", "Wilma"])
        portal_url = url_builder.build_portal_url("occurrence/search", params)
        assert portal_url == "https://gbif.org/occurrence/search?recordedBy=Fred&recordedBy=Wilma"


def test_complex_search_params(url_builder):
    """Test complex search parameters with multiple filters."""
    params = GBIFOccurrenceSearchParams(  # type: ignore
        scientificName=["Homo sapiens"],
        basisOfRecord=[BasisOfRecordEnum.HUMAN_OBSERVATION],
        continent=[ContinentEnum.EUROPE],
        country=["US"],
        year="2020,2023",
        decimalLatitude="30,50",
        decimalLongitude="-100,-50",
        hasCoordinate=True,
        occurrenceStatus=OccurrenceStatusEnum.PRESENT,
        license=[LicenseEnum.CC0_1_0],
        limit=20,
        offset=40,
    )

    api_params = url_builder._convert_to_api_params(params)

    # Verify key parameters are correctly converted
    assert api_params["scientificName"] == ["Homo sapiens"]
    assert api_params["basisOfRecord"] == ["HUMAN_OBSERVATION"]
    assert api_params["continent"] == ["EUROPE"]
    assert api_params["country"] == ["US"]
    assert api_params["year"] == ["2020,2023"]
    assert api_params["decimalLatitude"] == "30,50"
    assert api_params["decimalLongitude"] == "-100,-50"
    assert api_params["hasCoordinate"] == "true"
    assert api_params["occurrenceStatus"] == "PRESENT"
    assert api_params["license"] == ["CC0_1_0"]
    assert api_params["limit"] == 20
    assert api_params["offset"] == 40
