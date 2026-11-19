import asyncio
from typing import Any

import requests
from ichatbio.agent_response import IChatBioAgentProcess
from src.log import logger


def execute_sync_request(url: str, max_retries: int = 3) -> dict[str, Any]:
    """Execute a sync request with retry logic for 500 status codes."""
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, timeout=30)

            if response.status_code >= 500:
                if attempt < max_retries:
                    logger.warning(
                        f"Got {response.status_code} status, retrying (attempt {attempt + 1}/{max_retries})"
                    )
                    continue
                else:
                    response.raise_for_status()

            response.raise_for_status()
            result = response.json()
            # Handle both dict and list responses
            if isinstance(result, dict):
                result["status_code"] = response.status_code
                return result
            else:
                return {"data": result, "status_code": response.status_code}

        except requests.exceptions.HTTPError as e:
            if attempt == max_retries or (e.response and e.response.status_code < 500):
                raise
            logger.warning(
                f"Request failed: {e}, retrying (attempt {attempt + 1}/{max_retries})"
            )

    raise RuntimeError("Max retries exceeded")


async def execute_request(url: str) -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, execute_sync_request, url)


async def execute_multiple_requests(urls: dict[str, str]) -> dict[str, Any]:
    tasks = []
    for endpoint_name, url in urls.items():
        tasks.append(execute_request(url))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    combined_results = {}
    for endpoint_name, result in zip(urls.keys(), results):
        if isinstance(result, Exception):
            combined_results[endpoint_name] = {"error": str(result)}
        else:
            combined_results[endpoint_name] = result

    return combined_results


async def fetch_gbif_data(url: str, timeout: int = 30) -> dict[str, Any]:
    return await execute_request(url)


async def execute_paginated_request(
        search_params, api, total_limit: int, process: IChatBioAgentProcess
) -> dict[str, Any]:
    """
    Execute multiple paginated requests to fetch up to total_limit records.
    Fetches 5 pages concurrently at a time for better performance.

    Returns:
        Combined response dictionary with all results and updated metadata
    """
    batch_size = 300
    pages_per_batch = 5
    initial_offset = search_params.offset or 0
    offset = initial_offset
    all_results = []
    first_response_metadata = None

    while len(all_results) < total_limit:
        page_requests = []
        current_offset = offset

        for _ in range(pages_per_batch):
            remaining = total_limit - len(all_results) - len(page_requests) * batch_size
            if remaining <= 0:
                break

            this_limit = min(batch_size, remaining)
            paginated_params = search_params.model_copy(
                update={"limit": this_limit, "offset": current_offset}
            )
            request_url = api.build_occurrence_search_url(paginated_params)
            page_requests.append((request_url, current_offset))
            current_offset += this_limit

        if not page_requests:
            break

        await process.log(
            f"Fetching {len(page_requests)} pages starting at offset {offset}"
        )
        try:
            responses = await asyncio.gather(
                *[execute_request(url) for url, _ in page_requests],
                return_exceptions=True,
            )
        except Exception as e:
            if all_results:
                break
            raise e

        end_of_records = False
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                if all_results:
                    end_of_records = True
                    break
                raise response

            if first_response_metadata is None:
                first_response_metadata = {
                    "count": response.get("count", 0),
                    "endOfRecords": response.get("endOfRecords", False),
                    "status_code": response.get("status_code", 200),
                }

            batch_results = response.get("results", [])
            if not batch_results:
                end_of_records = True
                break

            all_results.extend(batch_results)

            if response.get("endOfRecords", False) or len(batch_results) < batch_size:
                end_of_records = True
                break

            offset = page_requests[i][1] + len(batch_results)

        if end_of_records:
            break

    combined_response = {
        "offset": initial_offset,
        "limit": total_limit,
        "endOfRecords": len(all_results) < total_limit,
        "count": (
            first_response_metadata.get("count", len(all_results))
            if first_response_metadata
            else len(all_results)
        ),
        "results": all_results,
        "status_code": (
            first_response_metadata.get("status_code", 200)
            if first_response_metadata
            else 200
        ),
        "facets": [],
    }

    return combined_response
