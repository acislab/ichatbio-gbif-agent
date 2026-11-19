import uuid

from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentEntrypoint

from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request
from src.models.validators import DatasetSearchParamsValidator
from src.log import with_logging, logger
from src.gbif.parser import parse


description = """
**Use Case:** Use this entrypoint to find datasets, collections, or other data sources in the GBIF Registry based on their metadata (e.g., title, publishing country, license).

**Triggers On:** User requests to "find datasets," "search for collections," or "list data sources about" a topic. Also handles requests for summaries of datasets (e.g., "count of datasets by type").

**Crucial Distinction:** Use this tool only when the user is asking about the data containers (datasets) themselves, not the individual data points inside them (occurrences or species records).

**Key Inputs:** A query string (q) and/or a wide variety of filters like type, keyword, publishingCountry, license, and taxonKey. It also supports faceting via the facet parameter.
"""

entrypoint = AgentEntrypoint(
    id="find_datasets",
    description=description
)


@with_logging("find_datasets")
async def run(context: ResponseContext, request: str):
    """
    Executes the dataset search entrypoint. Searches for datasets using the provided
    parameters and creates an artifact with the results.
    """
    async with context.begin_process("Requesting GBIF Dataset Search") as process:
        AGENT_LOG_ID = f"FIND_DATASETS_{str(uuid.uuid4())[:6]}"
        logger.info(f"Agent log ID: {AGENT_LOG_ID}")
        await process.log(
            f"Request received: {request} \n\nGenerating iChatBio for GBIF request parameters..."
        )

        response = await parse(request, entrypoint.id, DatasetSearchParamsValidator)
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

        api_url = api.build_dataset_search_url(params)
        await process.log(f"Constructed API URL: {api_url}")

        try:
            await process.log("Querying GBIF for dataset data...")
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

            total = raw_response.get("count", 0)
            portal_url = api.build_portal_url("dataset/search", params)

            page_info = {
                "count": total,
                "limit": params.limit,
                "offset": params.offset,
            }
            pagination_message = "API pagination information of the response"
            if page_info.get("count") > page_info.get("limit") + page_info.get(
                "offset"
            ):
                pagination_message = "Warning: The response is truncated due to pagination and only contain subset of the data available on GBIF."
            await process.log(pagination_message, data=page_info)

            await process.create_artifact(
                mimetype="application/json",
                description=description,
                uris=[api_url],
                metadata={
                    "portal_url": portal_url,
                    "source": "GBIF",
                },
            )

            summary = _generate_response_summary(total, portal_url)
            await context.reply(summary)

        except Exception as e:
            await process.log(
                f"Error during API request",
                data={
                    "error": str(e),
                    "agent_log_id": AGENT_LOG_ID,
                    "api_url": api_url,
                },
            )
            await context.reply(
                f"I encountered an error while trying to search for datasets: {str(e)}",
            )


def _generate_response_summary(total: int, portal_url: str) -> str:
    if total > 0:
        summary = (
            f"I have successfully searched for datasets and found matching records. "
        )
    else:
        summary = f"I have not found any datasets matching your criteria. "
    summary += f"The results can also be viewed in the GBIF portal at {portal_url}."
    return summary
