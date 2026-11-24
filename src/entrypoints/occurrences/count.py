import json
from dataclasses import dataclass
from typing import Iterable

from bionomia import normalize_name
from gadm.gadm import map_locations_to_gadm, serialize_locations
from gbif.api import GbifApi
from gbif.fetch import execute_request, execute_multiple_requests
from gbif.parser import parse
from gbif.resolve_parameters import resolve_names_to_taxonkeys, resolve_pending_search_parameters
from grscicoll import normalize_institution
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentEntrypoint
from log import with_logging
from models.entrypoints import GBIFOccurrenceFacetsParams
from models.validators import OccurrenceFacetsParamsValidator
from utils import (
    _preprocess_user_request,
    _generate_artifact_description,
    _generate_resolution_message,
    serialize_organisms,
    serialize_for_log,
    IdentifiedOrganismName,
    NamedEntityType,
)
from utils import serialize_entities

description = """
**Occurrence-based counts and distincts (supports location/time/record filters).**

- **Route to this when**: The user asks for counts or breakdowns that depend on where/when things were observed or any record-level constraints. This includes “unique/distinct taxa in [place],” “counts by country/year,” “top taxa by records,” or any occurrence-level filter (e.g., basisOfRecord, dataset, collector, coordinates).
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

Limitations: Returns aggregated summaries over occurrence records. For full record details, use the record/search endpoints.
"""

entrypoint = AgentEntrypoint(
    id="count_occurrence_records",
    description=description
)


@dataclass
class ParameterResolutionResult:
    search_params: GBIFOccurrenceFacetsParams | None
    clarification_needed: bool
    clarification_message: str | None = None


@with_logging("count_occurrence_records")
async def run(context: ResponseContext, request: str):
    """
    Executes the occurrence counting entrypoint. Counts occurrence records using the provided
    parameters and creates an artifact with the faceted results.
    """

    async with context.begin_process("Requesting GBIF statistics") as process:
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

        llm_generation = await parse(
            expandedRequest,
            entrypoint.id,
            OccurrenceFacetsParamsValidator,
            expansion_response,
        )

        await process.log(f"Parameter parsing plan", data={"plan": llm_generation.plan})
        api = GbifApi()

        param_result = await _get_parameters(
            llm_generation,
            request=expandedRequest,
            names=expansion_response.organisms,
            api=api,
            process=process,
        )

        await process.log(f"Search API parameter generation results:", data=serialize_for_log(param_result))

        abort = False
        if param_result.search_params is None:
            await context.reply("Failed to generate search parameters")
            abort = True

        if param_result.clarification_needed:
            await context.reply(param_result.clarification_message)
            abort = True

        if abort:
            return

        search_params: GBIFOccurrenceFacetsParams = param_result.search_params

        try:
            api_url = api.build_occurrence_facets_url(search_params)
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

            await process.log("Looking up scientific names for any received taxon keys")
            await _enrich_facets_with_names(api, process, raw_response["facets"])

            portal_url = api.build_portal_url("occurrence/search", search_params)
            matching_record_count = raw_response.get("count", 0)
            await process.log(f"Facet counts were computed over {matching_record_count} matching occurrence records."
                              f" these records can be viewed in the GBIF portal at {portal_url}")

            artifact_description = await _generate_artifact_description("\n\n".join([
                f"User request: {request}",
                f"Identified organisms in the request: {json.dumps(serialize_organisms(expansion_response.organisms))}",
                f"API search parameters used: {json.dumps(serialize_for_log(search_params))}"
            ]))

            # TODO: process.log warning only if facet limit is reached for any facet
            facet_offset = search_params.facetOffset or 0
            facet_limit = search_params.facetLimit or 10  # TODO: no magic numbers
            await process.log(f"Warning: only up to {facet_limit} counts are shown for each facet. If more counts are"
                              f" needed and available, make another request with a higher \"facetLimit\" or request"
                              f" the next page with facetOffset={facet_offset + facet_limit}")

            content_bytes = json.dumps(raw_response).encode("utf-8")
            await process.create_artifact(
                mimetype="application/json",
                description=artifact_description,
                content=content_bytes,
                metadata={
                    "derived_from": api_url,
                    "portal_url": portal_url,
                    "source": "GBIF",
                },
            )
        except Exception as e:
            # TODO: don't do this
            await process.log("Error during API request", data={"error": str(e), "api_url": api_url})
            await context.reply(f"I encountered an error while trying to count occurrences: {str(e)}")
            raise


async def _get_parameters(
        response: GBIFOccurrenceFacetsParams,
        request: str,
        names: list[IdentifiedOrganismName],
        process: IChatBioAgentProcess = None,
        api: GbifApi = None,
) -> ParameterResolutionResult:
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
        await process.log(f"Resolving {len(names)} names to taxon keys...")
        taxon_keys = await resolve_names_to_taxonkeys(api, names, process)
        if taxon_keys:
            params_updates.update(
                {
                    "taxonKey": taxon_keys,
                    "scientificName": None,
                }
            )
        else:
            await process.log(
                "Failed to resolve any scientific names to taxon keys, using original parameters"
            )

    # Single copy operation with all updates
    params = response.params.model_copy(update=params_updates)

    return ParameterResolutionResult(
        search_params=params,
        clarification_needed=clarification_needed,
        clarification_message=clarification_message
    )


async def _enrich_facets_with_names(api: GbifApi, process: IChatBioAgentProcess, facets: list):
    """Enrich facet results in-place by mapping taxon keys to scientific names."""

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

    for facet in facets:
        if facet.get("field", "") in taxonomic_facet_fields:
            counts = facet.get("counts", [])
            keys = {name for count in counts if (name := count.get("name"))}

            if keys:
                await process.log("Resolving taxon keys to scientific names", data={"keys": list(keys)})
                key_to_name = await resolve_keys_to_names(api, keys)
                await process.log(f"Resolved scientific names for {len(key_to_name)} of {len(keys)} taxon keys")

                for count in counts:
                    key = count.get("name")
                    if key in key_to_name:
                        count["scientificName"] = key_to_name[key]


async def resolve_keys_to_names(api: GbifApi, keys: Iterable[str]) -> dict[str, str]:
    """Resolve GBIF usage keys to scientific names using /v2/taxon."""
    if not keys:
        return {}

    urls = {key: api.build_species_key_search_url(key) for key in keys}
    results = await execute_multiple_requests(urls)

    return {
        key: info["scientificName"]
        for key, info in results.items()
        if isinstance(info, dict) and "scientificName" in info
    }
