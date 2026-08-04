import uuid
import json

from dataclasses import dataclass
from typing import Optional, List
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentEntrypoint

from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request
from src.models.entrypoints import GBIFOccurrenceFacetsParams
from src.models.validators import OccurrenceFacetsParamsValidator
from src.log import with_logging, logger
from src.utils import (
    _preprocess_user_request,
    _generate_artifact_description,
    _generate_resolution_message,
    serialize_organisms,
    serialize_for_log,
    IdentifiedOrganism,
    NamedEntityType,
)
from src.gbif.parser import parse
from src.gbif.param_normalizer import normalize_occurrence_params
from src.gbif.resolve_parameters import (
    resolve_names_to_taxonkeys,
    resolve_pending_search_parameters,
    resolve_keys_to_names,
)
from src.gadm.gadm import map_locations_to_gadm, serialize_locations
from src.bionomia import normalize_name
from src.grscicoll import normalize_institution
from src.utils import serialize_entities


description = """
**Occurrence-based counts and distincts (supports location/time/record filters).**

- **Route to this when**: The user asks for counts or breakdowns that depend on where/when things were observed or any record-level constraints. This includes “unique/distinct species in [place],” “counts by country/year,” “top taxa by records,” or any occurrence-level filter (e.g., basisOfRecord, dataset, collector, coordinates).
- **Do NOT use when**: The user wants purely taxonomic counts that are independent of observations. Those go to species counts.

**Use Case:** Aggregate GBIF occurrence records with facets; can compute distinct species (via `scientificName`/`TAXON_KEY` facets) under spatial/temporal/record filters.

**Triggers On (strong):** Mentions of place (country/GADM/geometry), “in/within/near [place],” dates/years, “records/occurrences/observed/collected/specimens,” sampling/protocol/dataset/elevation.
**Avoid If Present:** Purely taxonomic-only requests without any spatial/temporal/record context (route to species counts).

**Examples (choose THIS):**
- “How many unique plant species in Gainesville?”
- “Distinct species recorded in Kenya in 2020.”
- “Breakdown of occurrence records by basisOfRecord for birds in Brazil.”
- “Top 10 species by occurrences within 50 km of Madrid.”

**Examples (choose the OTHER entrypoint):**
- “How many genera are in Plantae?”
- “Number of endangered bird species worldwide.”
- “Taxonomic breakdown of Mammalia by rank.”

Limitations: Returns aggregated summaries over occurrence records; not the same as the taxonomic backbone counts. For full record details, use the record/search endpoints.
"""


entrypoint = AgentEntrypoint(
    id="count_occurrence_records",
    description=description
)


@dataclass
class ParameterResolutionResult:
    search_params: Optional[GBIFOccurrenceFacetsParams]
    clarification_needed: bool
    clarification_message: str = None


@with_logging("count_occurrence_records")
async def run(context: ResponseContext, request: str):
    """
    Executes the occurrence counting entrypoint. Counts occurrence records using the provided
    parameters and creates an artifact with the faceted results.
    """

    async with context.begin_process("Requesting GBIF statistics") as process:
        AGENT_LOG_ID = f"COUNT_OCCURRENCE_RECORDS_{str(uuid.uuid4())[:6]}"
        logger.info(f"Agent log ID: {AGENT_LOG_ID}")
        await process.log(f"Request recieved: {request} \n\nParsing request...")

        expansion_response = await _preprocess_user_request(request)
        enrich_locations = []
        if expansion_response.locations:
            enrich_locations = await map_locations_to_gadm(expansion_response.locations)
        if expansion_response.entities:
            for entity in expansion_response.entities:
                if entity.type is NamedEntityType.PERSON:
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
            OccurrenceFacetsParamsValidator,
            expansion_response,
        )

        logger.info(f"Parameter parsing plan: {response}")
        await process.log(f"Parameter parsing plan", data={"plan": response.plan})
        api = GbifApi()

        param_result = await _get_parameters(
            response,
            request=expandedRequest,
            organisms=expansion_response.organisms,
            api=api,
            process=process,
        )

        await process.log(
            f"Search API parameters results -",
            data=serialize_for_log(param_result),
        )

        if param_result.clarification_needed:
            await context.reply(param_result.clarification_message)
            return

        search_params = param_result.search_params

        api_url = api.build_occurrence_facets_url(search_params)

        try:
            await process.log(f"Sending data retrieval request to GBIF -", data={"url": api_url})
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

            await process.log("Resolving facet keys to scientific names if applicable")
            facets = raw_response.get("facets", [])
            enriched_facets = await _enrich_facets_with_names(api, process, facets)
            raw_response["facets"] = enriched_facets

            page_info = {
                "count": raw_response.get("count"),
                "facetLimit": search_params.facetLimit,
                "facetOffset": search_params.facetOffset,
            }
            pagination_message = "API pagination information of the response"
            if page_info.get("count") > (
                page_info.get("facetLimit") + page_info.get("facetOffset")
            ):
                pagination_message = "Warning: The response is truncated due to pagination and only contain subset of the data available on GBIF."
            await process.log(pagination_message, data=page_info)

            portal_url = api.build_portal_url("occurrence/search", search_params)

            artifact_description = await _generate_artifact_description(
                f"User request: {request} Identified organisms in the request: {json.dumps(serialize_organisms(expansion_response.organisms))}, Search parameters: {json.dumps(serialize_for_log(search_params))}, URL: {api_url}",
            )
            content_bytes = json.dumps(raw_response, indent=2).encode("utf-8")
            await process.create_artifact(
                mimetype="application/json",
                description=artifact_description,
                content=content_bytes,
                metadata={
                    "portal_url": portal_url,
                    "data_source": "GBIF Occurrence",
                },
            )

            summary = _generate_response_summary(page_info, portal_url)

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
                f"I encountered an error while trying to count occurrences: {str(e)}",
            )


def _generate_response_summary(page_info: dict, portal_url: str) -> str:
    if page_info.get("count") > 0:
        summary = f"I have found {page_info.get('count')} occurrence records matching your criteria. "
    else:
        summary = "I have not found any occurrence records matching your criteria. "
    summary += f"The results can also be viewed in the GBIF portal at {portal_url}."
    return summary


async def _get_parameters(
    response: GBIFOccurrenceFacetsParams,
    request: str,
    organisms: List[IdentifiedOrganism],
    process: IChatBioAgentProcess = None,
    api: GbifApi = None,
) -> ParameterResolutionResult:
    """
    Executes the occurrence facets entrypoint. Counts occurrence records using the provided
    parameters and creates an artifact with the faceted results.
    """
    resolved_fields = {}
    unresolved_fields = []
    clarification_message = None
    clarification_needed = response.clarification_needed

    # Collect all updates first, then do a single copy operation
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


async def _enrich_facets_with_names(
    api: GbifApi, process: IChatBioAgentProcess, facets: list
) -> list:
    """
    Enrich facet results by adding scientific names for taxonomic key facets.
    """
    taxonomic_facet_fields = {
        "SPECIES_KEY",
        "GENUS_KEY",
        "FAMILY_KEY",
        "ORDER_KEY",
        "CLASS_KEY",
        "PHYLUM_KEY",
        "KINGDOM_KEY",
        "TAXON_KEY",
    }

    enriched_facets = []

    for facet in facets:
        field = facet.get("field", "")
        if field in taxonomic_facet_fields:
            counts = facet.get("counts", [])
            keys = [int(count.get("name")) for count in counts if count.get("name")]

            if keys:
                key_to_name = await resolve_keys_to_names(api, process, keys, field)
                enriched_counts = []
                for count in counts:
                    key = count.get("name")
                    if key and int(key) in key_to_name:
                        enriched_count = count.copy()
                        enriched_count["scientificName"] = key_to_name[int(key)]
                        enriched_counts.append(enriched_count)
                    else:
                        enriched_counts.append(count)
                enriched_facet = facet.copy()
                enriched_facet["counts"] = enriched_counts
                enriched_facets.append(enriched_facet)
            else:
                enriched_facets.append(facet)
        else:
            enriched_facets.append(facet)
    return enriched_facets
