import json
import uuid

from gbif.api import GbifApi
from gbif.fetch import execute_request
from gbif.parser import parse
from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentEntrypoint
from log import with_logging, logger
from models.validators import SpeciesFacetsParamsValidator
from utils import _preprocess_user_request, serialize_organisms

description = """
**Species counts (taxonomic registry only — no location/time filters).**

- **Route to this when**: The user wants counts of taxonomic entities (e.g., species/genera/families) based on taxonomy or status, independent of where/when they were observed. Examples include “how many species in Plantae?”, “number of endangered bird species worldwide,” “breakdown by rank.”
- **Do NOT use when**: The prompt includes any location, date/time, geospatial constraint, or mentions occurrences/records/observations/collected/specimens. Those must go to occurrence-based counting.

**Use Case:** Count taxon name usages (taxonomic entities), not observations. Returns aggregated counts and facets.

**Triggers On (strong):** “how many species/genera/families,” “unique taxa (globally),” “by rank,” “by status,” “taxonomic breakdown,” “distinct taxa (no place/time).”
**Avoid If Present:** “in/within/near [place],” country/geometry/GADM, year/date/temporal filters, “records/occurrences/observed/collected/specimens.”

**Examples (choose THIS):**
- “How many genera are in Plantae?”
- “Number of endangered bird species worldwide.”
- “Breakdown of species by rank within Mammalia.”

**Examples (**MUST** choose the OTHER entrypoint):**
- “How many unique plant species in Gainesville?”
- “Distinct species recorded in Kenya in 2020.”
- “Top species by records near Paris.”

Limitations: Cannot filter by location, time, or record-level fields; does not guarantee presence/observation. It summarizes taxonomic entities only.
"""

entrypoint = AgentEntrypoint(
    id="count_species_records",
    description=description
)


@with_logging("count_species_records")
async def run(context: ResponseContext, request: str):
    """
    Executes the species counting entrypoint. Counts species name usage records using the provided
    parameters and creates an artifact with the faceted statistical results.
    """
    async with context.begin_process("Requesting GBIF Species statistics") as process:
        AGENT_LOG_ID = f"COUNT_SPECIES_RECORDS_{str(uuid.uuid4())[:6]}"
        await process.log(f"Request received: {request} \n\nParsing request...")

        expansion_response = await _preprocess_user_request(request)
        if expansion_response.locations:
            await process.log(
                "Warning: Request includes locations. This entrypoint cannot search for species records with specific locations."
            )
            await context.reply(
                "Warning: Request includes locations. This entrypoint cannot search for species records with specific locations. Please use occurrence search entrypoint instead."
            )
            return

        expanded_request = f"User request: {request} Identified organisms in the request: {json.dumps(serialize_organisms(expansion_response.organisms))}"
        await process.log(
            f"Expanded request",
            data={
                "original_request": request,
                "identified_organisms": serialize_organisms(
                    expansion_response.organisms
                ),
            },
        )

        response = await parse(
            expanded_request,
            entrypoint.id,
            SpeciesFacetsParamsValidator,
            expansion_response,
        )
        logger.info(f"Parameter parsing plan: {response}")
        await process.log(f"Parameter parsing plan", data={"plan": response.plan})
        if response.clarification_needed:
            await process.log(
                f"Clarification needed",
                data={"clarification_reason": response.clarification_reason},
            )
            await context.reply(f"{response.clarification_reason}")
            return

        await process.log(
            f"Final Search Parameters",
            data=response.params.model_dump(exclude_none=True),
        )
        params = response.params
        description = response.artifact_description

        api = GbifApi()
        api_url = api.build_species_facets_url(params)
        await process.log(f"Generated API URL: {api_url}")

        try:
            await process.log(f"Sending data retrieval request to {api_url}...")
            raw_response = await execute_request(api_url)
            status_code = raw_response.get("status_code", 200)
            if status_code != 200:
                await process.log(
                    f"Data retrieval failed with status code {status_code}",
                    data=raw_response,
                )
                await context.reply(
                    f"Data retrieval failed with status code {status_code}",
                )
                return
            await process.log(f"Data retrieval successful, status code {status_code}")
            # create a log of some informative fields from the response about the record
            page_info = {
                "count": raw_response.get("count"),
                "facetLimit": params.facetLimit,
                "facetOffset": params.facetOffset,
            }
            pagination_message = "API pagination information of the response"
            if page_info.get("count") > (
                    page_info.get("facetLimit") + page_info.get("facetOffset")
            ):
                pagination_message = "Warning: The response is truncated due to pagination and only contain subset of the data available on GBIF."
            await process.log(pagination_message, data=page_info)

            portal_url = api.build_portal_url("species/search", params)

            await process.create_artifact(
                mimetype="application/json",
                description=description,
                uris=[api_url],
                metadata={
                    "portal_url": portal_url,
                    "source": "GBIF",
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
                f"I encountered an error while trying to count species records: {str(e)}",
            )


def _generate_response_summary(page_info: dict, portal_url: str) -> str:
    if page_info.get("count") > 0:
        summary = f"I have found {page_info.get('count')} species records matching your criteria. "
    else:
        summary = "I have not found any species records matching your criteria. "
    summary += f"The results can also be viewed in the GBIF portal at {portal_url}."
    return summary
