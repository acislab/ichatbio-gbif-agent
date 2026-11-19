"""
GrSciColl Institution Normalization - Simple single function
"""

from ichatbio.agent_response import IChatBioAgentProcess
from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request
from src.models.grscicoll import GrSciCollInstitutionRecord
from src.models.registry import GBIFGrSciCollInstitutionSearchParams


async def normalize_institution(
        process: IChatBioAgentProcess, institution_name: str, limit: int = 20
) -> GrSciCollInstitutionRecord | None:
    """
    Normalize an institution name using GBIF GrSciColl API.

    Args:
        process: The agent process for logging
        institution_name: The institution name to normalize
        limit: Maximum number of results to return, default 20
    """
    await process.log(
        "Searching GBIF GrSciColl API for institution",
        data={"institution_name": institution_name}
    )

    try:
        api = GbifApi()
        params = GBIFGrSciCollInstitutionSearchParams(name=institution_name, limit=limit)
        api_url = api.build_grscicoll_institution_search_url(params)
        await process.log("Constructed GrSciColl API URL", data={"url": api_url})
        response = await execute_request(api_url)

        # Execute_request adds status_code to dict responses directly
        # For GBIF API, response structure is: {"count": ..., "results": [...], "status_code": ...}
        status_code = response.get("status_code", 200)
        if status_code != 200:
            await process.log(
                f"GrSciColl API returned status code {status_code}",
                data=response,
            )
            return None

        # Extract results from the response
        results_data = response.get("results", [])
        count = response.get("count", 0)

        # Convert to GrSciCollInstitutionRecord objects
        candidates: list[GrSciCollInstitutionRecord] = [
            (
                GrSciCollInstitutionRecord(**candidate)
                if isinstance(candidate, dict)
                else candidate
            )
            for candidate in results_data
        ]

        await process.log(
            f"GrSciColl returned {len(candidates)} candidates (total available: {count})"
        )

        if not candidates:
            # No results found
            await process.log(
                f"No GrSciColl matches found for '{institution_name}'"
            )
            return None

        # Use the first result (no matching logic needed)
        institution = candidates[0]
        await process.log(
            f"Found institution '{institution.name}' (code: {institution.code}, key: {institution.key})"
        )
        return institution

    except Exception as e:
        await process.log(f"Error in institution normalization: {str(e)}")
        return None
