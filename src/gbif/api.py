"""
GBIF API URL Builder Module
"""

from typing import Dict, Any
from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel

from src.models.entrypoints import (
    GBIFOccurrenceSearchParams,
    GBIFOccurrenceFacetsParams,
    GBIFSpeciesNameMatchParams,
    GBIFSpeciesSearchParams,
    GBIFSpeciesFacetsParams,
    GBIFSpeciesTaxonomicParams,
    GBIFOccurrenceByIdParams,
    GBIFDatasetSearchParams,
)
from src.models.registry import GBIFGrSciCollInstitutionSearchParams


class GbifApi:
    def __init__(self):
        self.base_url = "https://api.gbif.org"
        self.portal_url = "https://gbif.org"

    def _convert_to_api_params(self, params: BaseModel, with_checklist=False) -> Dict[str, Any]:
        api_params = {}

        for field_name, value in params.model_dump(by_alias=True).items():
            if value is None:
                continue

            if isinstance(value, list):
                processed_values = []
                for item in value:
                    if hasattr(item, "value"):
                        processed_values.append(item.value)
                    elif isinstance(item, UUID):
                        processed_values.append(str(item))
                    elif isinstance(item, bool):
                        processed_values.append(str(item).lower())
                    else:
                        processed_values.append(item)
                api_params[field_name] = processed_values
            elif hasattr(value, "value"):
                api_params[field_name] = value.value
            elif isinstance(value, UUID):
                api_params[field_name] = str(value)
            elif isinstance(value, bool):
                api_params[field_name] = str(value).lower()
            else:
                api_params[field_name] = value

        # Use "CoL XR" taxon IDs instead of GBIF backbone IDs. This is only needed for the API, not the search portal
        if with_checklist:
            api_params["checklistKey"] = "7ddf754f-d193-4cc9-b351-99906754a03b"

        return api_params

    def _make_api_url(self, endpoint: str, parameters: dict | None = None):
        query_string = urlencode(parameters or {}, doseq=True)
        return f"{self.base_url}{endpoint}?{query_string}"

    def build_occurrence_search_url(self, params: GBIFOccurrenceSearchParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        return self._make_api_url("/v1/occurrence/search", api_params)

    def build_occurrence_facets_url(self, params: GBIFOccurrenceFacetsParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        api_params["limit"] = 0
        return self._make_api_url("/v1/occurrence/search", api_params)

    def build_species_search_url(self, params: GBIFSpeciesSearchParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        return self._make_api_url("/v1/species/search", api_params)

    def build_species_facets_url(self, params: GBIFSpeciesFacetsParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        api_params["limit"] = 0
        return self._make_api_url("/v1/species/search", api_params)

    def build_species_key_search_url(self, col_xr_key: str) -> str:
        return self._make_api_url(f"/v1/species/{col_xr_key}")

    def build_species_taxonomic_urls(
            self, params: GBIFSpeciesTaxonomicParams
    ) -> Dict[str, str]:
        if not params.key:
            return {}

        usage_key = params.key
        base_url = self.build_species_key_search_url(usage_key)
        urls = {
            "basic": f"{base_url}",
            "parsed_name": f"{base_url}/name",
        }
        if params.includeParents:
            urls["parents"] = f"{base_url}/parents"
        if params.includeChildren:
            urls["children"] = (
                f"{base_url}/children?limit={params.limit}&offset={params.offset}"
            )
        if params.includeSynonyms:
            urls["synonyms"] = (
                f"{base_url}/synonyms?limit={params.limit}&offset={params.offset}"
            )
        return urls

    def build_species_match_url(self, params: GBIFSpeciesNameMatchParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        return self._make_api_url("/v2/species/match", api_params)

    def build_occurrence_by_id_url(self, gbif_id: int) -> str:
        return self._make_api_url(f"/v1/occurrence/{gbif_id}")

    def build_dataset_search_url(self, params: GBIFDatasetSearchParams) -> str:
        api_params = self._convert_to_api_params(params, with_checklist=True)
        return self._make_api_url("/v1/dataset/search", api_params)

    def build_grscicoll_institution_search_url(
            self, params: GBIFGrSciCollInstitutionSearchParams
    ) -> str:
        api_params = self._convert_to_api_params(params)
        return self._make_api_url("/v1/grscicoll/institution/search", api_params)

    def build_portal_url(self, path: str, params: BaseModel | None) -> str:
        """Convert an API URL to its corresponding portal URL."""
        base_url = f"{self.portal_url}/{path}"
        dict_params = params.model_dump(exclude_none=True) if params is not None else {}

        # Remove facet-related and limit parameters
        dict_params = {key: value for key, value in dict_params.items() if key not in {
            "limit",
            "facet",
            "facetLimit",
            "facetOffset",
            "facetMincount",
            "facetMultiselect",
        }}

        # Construct portal URL
        if dict_params:
            arguments = "&".join(
                "&".join((f"{parameter}={v}" for v in _as_list(value)))
                for parameter, value in dict_params.items()
                if value
            )
            return f"{base_url}?{arguments}&advanced=true"

        return base_url


def _as_list(value):
    return value if isinstance(value, list) else [value]
