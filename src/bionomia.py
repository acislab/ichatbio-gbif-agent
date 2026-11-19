"""
Bionomia Name Normalization - Simple single function
"""
import requests
from ichatbio.agent_response import IChatBioAgentProcess
from src.gbif.fetch import execute_request
from src.models.bionomia import BionomiaNameRecord
from src.utils import find_best_name_match


async def normalize_name(
        process: IChatBioAgentProcess, name: str, threshold: float = 0.7, timeout: int = 10
) -> dict:
    """
    Normalize a collector/determiner name using Bionomia API.

    Args:
        name: The name to normalize
        threshold: Minimum similarity threshold (0-1), default 0.7
        timeout: Request timeout in seconds, default 10
    """
    await process.log("Searching Bionomia API for name", data={"name": name})

    try:
        # Search Bionomia API
        url = f"https://api.bionomia.net/user.json?q={name}&has_occurrences=true"
        await process.log("Constructed Bionomia API URL", data={"url": url})
        response = await execute_request(url)
        # Execute_request wraps list responses in {"data": [...], "status_code": ...}
        # For Bionomia API, we expect a list wrapped in "data"
        if isinstance(response, dict) and "data" in response:
            candidates_data = response["data"]
        elif isinstance(response, list):
            # Fallback: if response is directly a list (shouldn't happen with current fetch.py)
            candidates_data = response
        else:
            candidates_data = []

        # Convert to BionomiaNameRecord objects
        candidates: list[BionomiaNameRecord] = [
            (
                BionomiaNameRecord(**candidate)
                if isinstance(candidate, dict)
                else candidate
            )
            for candidate in candidates_data
        ]

        await process.log(f"Bionomia returned {len(candidates)} candidates")
        if not candidates:
            return {"status": "not_found", "original": name}

        if len(candidates) == 1:
            return candidates[0].model_dump(exclude_none=True)

        await process.log(
            'Warning: Searching for the best match; please use "quotes" to do strict name matching search.'
        )
        try:
            result = await find_best_name_match(name, candidates)
            top_matches = result["matches"]
            await process.log("LLM", {"reflection": result["monologue"]})
            # Sort matches by 'match_confidence' in descending order, and log only the best one
            sorted_matches = sorted(
                top_matches, key=lambda x: x.get("match_confidence", 0), reverse=True
            )
            best_match = sorted_matches[0] if sorted_matches else None
            await process.log(
                f"Best name match for {name}",
                data={"best_match": best_match},
            )

            if not best_match:
                return {
                    "status": "no_good_match",
                    "original": name,
                    "found_count": len(candidates),
                    "threshold": threshold,
                }

            # Return the match dict directly (already includes match_reason and score)
            return best_match
        except Exception as e:
            await process.log(f"Error in name matching: {str(e)}")
            # Fallback: return first candidate if matching fails
            return {
                "status": "match_failed",
                "original": name,
                "found_count": len(candidates),
                "error": str(e),
                "fallback": (
                    candidates[0].model_dump(exclude_none=True) if candidates else None
                ),
            }

    except requests.exceptions.RequestException as e:
        return {"status": "error", "original": name, "error": str(e)}
