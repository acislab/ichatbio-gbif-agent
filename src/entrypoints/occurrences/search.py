import uuid
import json
from typing import List
from dataclasses import dataclass
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentEntrypoint

from src.utils import IdentifiedOrganism
from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request, execute_paginated_request
from src.models.entrypoints import GBIFOccurrenceSearchParams
from src.models.validators import OccurrenceSearchParamsValidator
from src.log import with_logging, logger
from src.utils import (
    _generate_artifact_description,
    _generate_resolution_message,
    _preprocess_user_request,
    serialize_organisms,
    serialize_entities,
    serialize_for_log,
    NamedEntityType,
)
from src.gbif.parser import parse
from src.gbif.param_normalizer import normalize_occurrence_params
from src.gbif.resolve_parameters import (
    resolve_names_to_taxonkeys,
    resolve_pending_search_parameters,
)
from src.gadm.gadm import (
    map_locations_to_gadm,
    serialize_locations,
)
from src.bionomia import normalize_name
from src.grscicoll import normalize_institution


description = """
**Use Case:** Use this entrypoint to search for and retrieve a list of individual occurrence records that match specific filters. This is the primary tool for fetching raw data.

**Triggers On:** User requests that may ask to "find," "list," or "show records of" something. It's for when the user wants to see the actual data entries, not a summary of them. It may also ask for records of a specific species, location, or time period.

**Key Inputs:** Requires specific search criteria like scientificName, taxonKey, country, year, or geographic coordinates (latitude, longitude).

**Limitations:** This entrypoint does not perform summaries or counts. It also does not sort the results.
"""

entrypoint = AgentEntrypoint(
    id="find_occurrence_records",
    description=description
)


@with_logging("find_occurrence_records")
async def run(context: ResponseContext, request: str):
    """
    Executes the occurrence search entrypoint. Searches for occurrence records using the provided
    parameters and creates an artifact with the results.
    """

    async with context.begin_process("Requesting GBIF Occurrence Records") as process:
        AGENT_LOG_ID = f"FIND_OCCURRENCE_RECORDS_{str(uuid.uuid4())[:6]}"
        logger.info(f"Agent log ID: {AGENT_LOG_ID}")
        await process.log(f"Request recieved: {request} \n\nParsing request...")

        expansion_response = await _preprocess_user_request(request)
        enrich_locations = []
        if expansion_response.locations:
            enrich_locations = await map_locations_to_gadm(
                expansion_response.locations, process
            )
        if expansion_response.entities:
            for entity in expansion_response.entities:
                if entity.type is NamedEntityType.PERSON:
                    if entity.strict:
                        await process.log(
                            "User requested a strict match for a person name, skipping Bionomia lookup."
                        )
                        continue
                    else:
                        result = await normalize_name(process, entity.value)
                        # Check if result is a successful match (no status field means success)
                        if result.get("status") is None:
                            # Collect all name variants from the record
                            alternate_names = []
                            if result.get("fullname"):
                                alternate_names.append(result["fullname"])
                            if result.get("fullname_reverse"):
                                alternate_names.append(result["fullname_reverse"])
                            if result.get("label") and result["label"] != result.get(
                                "fullname"
                            ):
                                alternate_names.append(result["label"])
                            if result.get("other_names"):
                                alternate_names.extend(result["other_names"])
                            entity.alternate_names = alternate_names
                        else:
                            continue
                elif entity.type in (
                    NamedEntityType.INSTITUTION,
                    NamedEntityType.MUSEUM,
                    NamedEntityType.COLLECTION,
                ):
                    institution = await normalize_institution(process, entity.value)
                    if institution:
                        await process.log(
                            f"GrSciColl search result for {entity.value}",
                            data=institution.model_dump(exclude_none=True),
                        )
                        # Expand entity with institution code and key
                        if institution.code:
                            entity.institution_code = institution.code
                            await process.log(
                                f"Added institution_code: {institution.code}"
                            )
                        if institution.key:
                            entity.institution_key = institution.key
                            await process.log(
                                f"Added institution_key: {institution.key}"
                            )
                    else:
                        await process.log(
                            f"No GrSciColl match found for '{entity.value}', will use name as-is"
                        )
                        # If not found, entity.value remains as the original institution name (use as-is)
        expandedRequest = f"User request: {request} Identified organisms in the request: {json.dumps(serialize_organisms(expansion_response.organisms))} Identified locations in the request: {json.dumps(serialize_locations(enrich_locations))} Identified entities in the request: {json.dumps(serialize_entities(expansion_response.entities), indent=2)}"
        await process.log(
            f"Expanded request",
            data={
                "original_request": request,
                "identified_organisms": serialize_organisms(
                    expansion_response.organisms
                ),
                "identified_locations": serialize_locations(enrich_locations),
                "identified_entities": serialize_entities(expansion_response.entities),
            },
        )

        response = await parse(
            expandedRequest,
            entrypoint.id,
            OccurrenceSearchParamsValidator,
            expansion_response,
        )
        await process.log(f"Parameter parsing plan", data={"plan": response.plan})
        logger.info(f"Parameter parsing plan: {response}")
        api = GbifApi()

        param_result = await _get_parameters(
            response,
            request=expandedRequest,
            organisms=expansion_response.organisms,
            api=api,
            process=process,
        )

        if param_result.clarification_needed:
            await context.reply(param_result.clarification_message)
            return

        search_params = param_result.search_params

        await process.log(
            f"Final Search API parameters",
            data=serialize_for_log(search_params),
        )

        request_limit = search_params.limit
        multi_page_request = request_limit > 300
        SEED = 40
        search_params = search_params.model_copy(update={"shuffle": SEED})

        try:
            api_url = api.build_occurrence_search_url(search_params)
            if multi_page_request:
                await process.log(
                    f"Sending data retrieval requests to GBIF (limit: {request_limit}) -",
                    data={"total_limit": request_limit},
                )
                raw_response = await execute_paginated_request(
                    search_params, api, request_limit, process
                )
            else:
                await process.log(
                    f"Sending data retrieval request to GBIF -", data={"url": api_url}
                )
                raw_response = await execute_request(api_url)
            status_code = raw_response.get("status_code", 200)
            if status_code != 200:
                await process.log(
                    f"Data retrieval failed with status code {status_code} -",
                    data=raw_response,
                )
                await context.reply(
                    f"Data retrieval failed with status code {status_code}"
                )
                return
            await process.log(f"Data retrieval successful, status code {status_code}")
            # create a log of some informative fields from the response about the record
            page_info = {
                "count": raw_response.get("count"),
                "limit": raw_response.get("limit"),
                "offset": raw_response.get("offset"),
            }
            pagination_message = "API pagination information of the response"
            if page_info.get("count") > (
                page_info.get("limit") + page_info.get("offset")
            ):
                pagination_message = "Warning: The response is truncated due to pagination and only contain subset of the data available on GBIF."
            await process.log(pagination_message, data=page_info)

            portal_url = api.build_portal_url("occurrence/search", search_params)
            artifact_description = await _generate_artifact_description(request)

            if multi_page_request:
                await process.create_artifact(
                    mimetype="application/json",
                    description=artifact_description,
                    content=json.dumps(raw_response, indent=2).encode("utf-8"),
                    metadata={
                        "portal_url": portal_url,
                        "data_source": "GBIF Occurrence",
                        "total_records_retrieved": len(raw_response.get("results", [])),
                    },
                )
            else:
                await process.create_artifact(
                    mimetype="application/json",
                    description=artifact_description,
                    uris=[api_url],
                    metadata={
                        "portal_url": portal_url,
                        "data_source": "GBIF Occurrence",
                    },
                )

            summary = _generate_response_summary(
                page_info, portal_url, multi_page_request
            )

            await context.reply(summary)

        except Exception as e:
            await process.log(
                "Error during API request",
                data={
                    "error": str(e),
                    "agent_log_id": AGENT_LOG_ID,
                    "api_url": api_url,
                },
            )
            await context.reply(
                f"I encountered an error while trying to search for occurrences: {str(e)}",
            )


def _generate_response_summary(
    page_info: dict, portal_url: str, paginated: bool = False
) -> str:
    if page_info.get("count") > 0:
        if paginated:
            summary = f"I have successfully searched for occurrences and retrieved {page_info.get('limit')} records using pagination across multiple requests. Total records available in GBIF: {page_info.get('count')}. "
        else:
            summary = f"I have successfully searched for occurrences and matching records. Retrieved {page_info.get('limit')} records per page, {page_info.get('offset')} records offset. Total records found: {page_info.get('count')}. "
    else:
        summary = "I have not found any occurrence records matching your criteria. "
    summary += f"The results can also be viewed in the GBIF portal at {portal_url}."
    return summary


@dataclass
class ParameterResolutionResult:
    search_params: GBIFOccurrenceSearchParams
    clarification_needed: bool
    clarification_message: str = None


async def _get_parameters(
    response: GBIFOccurrenceSearchParams,
    organisms: List[IdentifiedOrganism] = None,
    api: GbifApi = None,
    process: IChatBioAgentProcess = None,
    request: str = None,
) -> ParameterResolutionResult:
    """
    Executes the occurrence search entrypoint. Searches for occurrence records using the provided
    parameters and creates an artifact with the results.
    """
    resolved_fields = {}
    unresolved_fields = []
    clarification_message = None
    clarification_needed = response.clarification_needed

    params_updates = {}

    if response.clarification_needed:
        await process.log(
            f"{response.clarification_reason} -",
            data={"unresolved_params": response.unresolved_params},
        )
        resolved_fields, unresolved_fields = await resolve_pending_search_parameters(
            response.unresolved_params or [], request, api, process
        )
        if resolved_fields:
            params_updates.update(resolved_fields)
        if unresolved_fields:
            # Create params with current updates for the early return case
            clarification_message = await _generate_resolution_message(
                request,
                response,
                resolved_fields,
                unresolved_fields,
            )
            return ParameterResolutionResult(
                search_params=None,
                clarification_needed=True,
                clarification_message=clarification_message,
            )
        else:
            await process.log(f"Request parsed successfully...")
            clarification_needed = False

    # Check if we need to resolve scientific names (before creating the final params)
    base_params = response.params.model_copy(update=params_updates)
    if getattr(base_params, "scientificName", None):
        await process.log(f"Resolving {len(organisms)} organisms to taxon keys...")
        taxon_keys = await resolve_names_to_taxonkeys(api, organisms, process)
        if taxon_keys:
            params_updates.update(
                {
                    "taxonKey": [int(key) for key in taxon_keys],
                    "scientificName": None,
                }
            )
        else:
            await process.log(
                "Failed to resolve any scientific names to taxon keys, using original parameters"
            )

    # Single copy operation with all updates
    params = response.params.model_copy(update=params_updates)
    params, normalization_report = await normalize_occurrence_params(params)

    if process and (normalization_report.matches or normalization_report.misses):
        await process.log(
            "Normalized vocabulary-backed occurrence parameters",
            data={
                "matches": [
                    match.__dict__ for match in normalization_report.matches
                ],
                "misses": [miss.__dict__ for miss in normalization_report.misses],
                "vocabularies_used": normalization_report.vocabularies_used,
            },
        )

    return ParameterResolutionResult(
        search_params=params,
        clarification_needed=clarification_needed,
        clarification_message=clarification_message,
    )
