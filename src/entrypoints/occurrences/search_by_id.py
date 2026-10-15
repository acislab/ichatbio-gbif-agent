import uuid

from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentEntrypoint

from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request
from src.models.validators import OccurrenceSearchByIdParamsValidator
from src.log import with_logging, logger
from src.gbif.parser import parse


description = """
**Use Case:** Use this entrypoint to retrieve one single, specific occurrence record by its unique GBIF identifier.

- **Triggers On:** User requests to "get details for ID," "look up occurrence," or "find record" when a specific GBIF ID (a number) is provided in the query.

**Key Inputs:** Requires a single, unique gbifId.

**Limitations:** This entrypoint only works with a GBIF ID. It cannot be used for general or filtered searches.
"""


entrypoint = AgentEntrypoint(
    id="find_occurrence_by_id",
    description=description
)


@with_logging("find_occurrence_by_id")
async def run(context: ResponseContext, request: str):
    """
    Executes the occurrence by ID entrypoint. Retrieves a single occurrence record using the provided
    GBIF ID and creates an artifact with the result.
    """
    async with context.begin_process("Requesting GBIF Occurrence by ID") as process:
        AGENT_LOG_ID = f"FIND_OCCURRENCE_BY_ID_{str(uuid.uuid4())[:6]}"
        logger.info(f"Agent log ID: {AGENT_LOG_ID}")
        await process.log(f"Request received: {request} \n\nParsing request...")

        response = await parse(
            request, entrypoint.id, OccurrenceSearchByIdParamsValidator
        )
        if response.clarification_needed:
            await process.log(f"Clarification needed: {response.clarification_reason}")
            await context.reply(f"{response.clarification_reason}")
            return

        params = response.params
        description = response.artifact_description

        await process.log(
            "Generated search parameters",
            data=params.model_dump(exclude_defaults=True),
        )

        api = GbifApi()

        api_url = api.build_occurrence_by_id_url(params.gbifId)
        await process.log(f"Constructed API URL: {api_url}")

        try:
            await process.log("Querying GBIF for occurrence data...")
            raw_response = await execute_request(api_url)
            status_code = raw_response.get("status_code", 200)
            if status_code == 404:
                await process.log(
                    "GBIF ID not found",
                    data=raw_response,
                )
                await context.reply(
                    "GBIF ID is not valid",
                )
                return
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
            subset_response = {
                "gbifID": raw_response.get("gbifID"),
                "scientificName": raw_response.get("scientificName"),
                "basisOfRecord": raw_response.get("basisOfRecord"),
                "occurrenceStatus": raw_response.get("occurrenceStatus"),
                "taxonomicStatus": raw_response.get("taxonomicStatus"),
                "elevation": raw_response.get("elevation"),
                "continent": raw_response.get("continent"),
                "stateProvince": raw_response.get("stateProvince"),
                "year": raw_response.get("year"),
                "kingdom": raw_response.get("kingdom"),
                "phylum": raw_response.get("phylum"),
                "datasetKey": raw_response.get("datasetKey"),
                "recordedBy": raw_response.get("recordedBy"),
                "publishingCountry": raw_response.get("publishingCountry"),
            }
            await process.log("Record information - ", data=subset_response)

            portal_url = f"{api.portal_url}/occurrence/{params.gbifId}"

            await process.create_artifact(
                mimetype="application/json",
                description=description,
                uris=[api_url],
                metadata={
                    "portal_url": portal_url,
                    "data_source": "GBIF Occurrence",
                },
            )

            summary = _generate_response_summary(params.gbifId, portal_url)
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
                f"I encountered an error while trying to retrieve the occurrence: {str(e)}",
            )


def _generate_response_summary(gbif_id: int, portal_url: str) -> str:
    summary = (
        f"I have successfully retrieved the occurrence record with GBIF ID {gbif_id}. "
    )
    summary += f"The result can also be viewed in the GBIF portal at {portal_url}."
    return summary
