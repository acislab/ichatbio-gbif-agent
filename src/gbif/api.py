"""
GBIF API URL Builder Module
"""
import logging
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from gbif.contants import COL_CHECKLIST_KEY
from httpx import AsyncClient
from models.entrypoints import (
    GBIFOccurrenceSearchParams,
    GBIFOccurrenceFacetsParams,
    GBIFSpeciesNameMatchParams,
    GBIFSpeciesSearchParams,
    GBIFSpeciesFacetsParams,
    GBIFSpeciesTaxonomicParams,
    GBIFDatasetSearchParams,
)
from models.registry import GBIFGrSciCollInstitutionSearchParams
from pydantic import BaseModel


class GbifApi:
    def __init__(self):
        self.base_url = "https://api.gbif.org"
        self.portal_url = "https://gbif.org"
        self.httpx_client = AsyncClient(follow_redirects=True, timeout=10.)

    async def get(self, url: str, max_attempts=3) -> httpx.Response:
        response = await self.httpx_client.get(url)
        if response.status_code >= 500:
            logging.warning(
                f"Got {response.status_code} status, retrying ({max_attempts} attempts remaining)"
            )
            return await self.get(url, max_attempts - 1)
        else:
            response.raise_for_status()

        return response

    def _convert_to_api_params(self, params: BaseModel, add_checklist: str | None = None) -> dict[str, Any]:
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
        if add_checklist and add_checklist not in api_params:
            api_params[add_checklist] = COL_CHECKLIST_KEY

        return api_params

    def _make_api_url(self, endpoint: str, parameters: dict | None = None):
        query_string = "?" + urlencode(parameters or {}, doseq=True) if parameters else ""
        return f"{self.base_url}{endpoint}{query_string}"

    def build_occurrence_search_url(self, params: GBIFOccurrenceSearchParams) -> str:
        api_params = self._convert_to_api_params(params, add_checklist="checklistKey")
        return self._make_api_url("/v1/occurrence/search", api_params)

    def build_occurrence_facets_url(self, params: GBIFOccurrenceFacetsParams) -> str:
        api_params = self._convert_to_api_params(params, add_checklist="checklistKey")
        api_params["limit"] = 0
        return self._make_api_url("/v1/occurrence/search", api_params)

    def build_species_search_url(self, params: GBIFSpeciesSearchParams) -> str:
        api_params = self._convert_to_api_params(params, add_checklist="datasetKey")
        return self._make_api_url("/v1/species/search", api_params)

    def build_species_facets_url(self, params: GBIFSpeciesFacetsParams) -> str:
        api_params = self._convert_to_api_params(params, add_checklist="datasetKey")
        api_params["limit"] = 0
        return self._make_api_url("/v1/species/search", api_params)

    def build_species_key_search_url(self, col_xr_key: str) -> str:
        return self._make_api_url(f"/v2/taxon/{COL_CHECKLIST_KEY}/{col_xr_key}")

    def build_species_taxonomic_urls(
            self, params: GBIFSpeciesTaxonomicParams
    ) -> dict[str, str]:
        if not params.key:
            return {}

        usage_key = params.key
        base_url = self.build_species_key_search_url(usage_key)
        urls = {
            "info": f"{base_url}/info",
        }
        return urls

    def build_species_match_url(self, params: GBIFSpeciesNameMatchParams) -> str:
        api_params = self._convert_to_api_params(params, add_checklist="checklistKey")
        return self._make_api_url("/v2/species/match", api_params)

    def build_occurrence_by_id_url(self, gbif_id) -> str:
        return self._make_api_url(f"/v1/occurrence/{gbif_id}")

    def build_dataset_search_url(self, params: GBIFDatasetSearchParams) -> str:
        api_params = self._convert_to_api_params(params)
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
            "shuffle",
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
            return f"{base_url}?{arguments}"

        return base_url


def _as_list(value):
    return value if isinstance(value, list) else [value]
