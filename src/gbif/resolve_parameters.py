from src.instructor_client import get_client
from src.models.entrypoints import GBIFSpeciesNameMatchParams
from src.utils import IdentifiedOrganism

"""
Module for resolving taxonomic names to GBIF keys automatically.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
from src.gbif.api import GbifApi
from src.gbif.fetch import execute_request
from ichatbio.agent_response import IChatBioAgentProcess


class TaxonomicExtraction(BaseModel):
    """Model for LLM-based taxonomic name extraction."""

    families: List[str] = Field(
        default=[],
        description="List of family names mentioned in the text (e.g., Apidae, Felidae, Ursidae)",
    )
    genera: List[str] = Field(
        default=[],
        description="List of genus names mentioned in the text (e.g., Homo, Quercus, Pinus)",
    )
    species: List[str] = Field(
        default=[],
        description="List of species names (binomial) mentioned in the text (e.g., Homo sapiens, Quercus alba)",
    )
    orders: List[str] = Field(
        default=[],
        description="List of order names mentioned in the text (e.g., Primates, Carnivora, Lepidoptera)",
    )
    classes: List[str] = Field(
        default=[],
        description="List of class names mentioned in the text (e.g., Mammalia, Aves, Insecta)",
    )
    phylums: List[str] = Field(
        default=[],
        description="List of phylum names mentioned in the text (e.g., Chordata, Arthropoda, Mollusca)",
    )
    kingdoms: List[str] = Field(
        default=[],
        description="List of kingdom names mentioned in the text (e.g., Animalia, Plantae, Fungi)",
    )
    note: str = Field(
        default="",
        description="Note about the taxonomic names extracted; why you extracted them",
    )


taxonomic_extraction_prompt = """You are a taxonomic expert. Extract all taxonomic names mentioned in the user's request.

- Only extract names that are clearly taxonomic, not common names
- Be conservative - only extract names you're confident about
- Return empty lists for ranks not mentioned in the text

Examples:
- "bees (family: Apidae, Andrenidae)" → families: ["Apidae", "Andrenidae"]
- "Homo sapiens and Pan troglodytes" → species: ["Homo sapiens", "Pan troglodytes"], genera: ["Homo", "Pan"]
- "order Carnivora" → orders: ["Carnivora"]
- "butterflies from family Nymphalidae" → families: ["Nymphalidae"]"""

resolvable_fields = {
    "familyKey": "family",
    "genusKey": "genus",
    "speciesKey": "species",
    "orderKey": "order",
    "classKey": "class",
    "phylumKey": "phylum",
    "kingdomKey": "kingdom",
    # ... add more taxonomic fields here
}


async def resolve_field_from_request(
        api: GbifApi, process: IChatBioAgentProcess, field_name: str, user_request: str
) -> Optional[List[int]]:
    if field_name not in resolvable_fields:
        return None
    rank = resolvable_fields[field_name]
    extraction = await extract_taxonomic_names(process, user_request)
    rank_mapping = {
        "family": extraction.families,
        "genus": extraction.genera,
        "species": extraction.species,
        "order": extraction.orders,
        "class": extraction.classes,
        "phylum": extraction.phylums,
        "kingdom": extraction.kingdoms,
    }
    names = rank_mapping.get(rank, [])
    if not names:
        return None

    resolved_keys = []
    for name in names:
        key = await resolve_name_to_key(api, process, name, rank)
        if key:
            resolved_keys.append(key)
            await process.log(f"Resolved {rank} '{name}' to {key}")
        else:
            await process.log(f"Failed to resolve {rank} '{name}'")
    return resolved_keys if resolved_keys else None


async def extract_taxonomic_names(
        process: IChatBioAgentProcess, user_request: str
) -> TaxonomicExtraction:
    await process.log("Diving deeper...")
    try:
        openai_client = await get_client()
        messages = [
            {"role": "system", "content": taxonomic_extraction_prompt},
            {
                "role": "user",
                "content": f"Identified taxonomy: {user_request}",
            },
        ]
        response = await openai_client.chat.completions.create(
            messages=messages,
            response_model=TaxonomicExtraction,
        )
        await process.log(f"Taxonomic names extracted", data=response.model_dump())
        return response
    except Exception as e:
        await process.log(
            f"LLM extraction failed, falling back to empty extraction: {str(e)}"
        )
        return TaxonomicExtraction()


async def resolve_name_to_key(
        api: GbifApi, process: IChatBioAgentProcess, name: str, expected_rank: str
) -> Optional[int]:
    try:
        params = GBIFSpeciesNameMatchParams(scientificName=name)
        url = api.build_species_match_url(params)
        await process.log(f"Attempting to resolve {expected_rank} names: {name}", data={'url': url})
        result = await execute_request(url)
        await process.create_artifact(
            mimetype="application/json",
            description=f"GBIF Species Match API call results for: {name}",
            uris=[url],
            metadata={
                "source": "GBIF",
            },
        )
        if result.get("usage") and result.get("usage", {}).get("key"):
            usage = result["usage"]
            key = usage.get("key")
            rank = usage.get("rank", "").lower()
            if rank == expected_rank.upper() or rank == expected_rank.lower():
                return key
            else:
                await process.log(
                    f"Rank mismatch for '{name}' expected {expected_rank}, got {rank}"
                )
                return None
        return None
    except Exception as e:
        await process.log(f"Error resolving '{name}': {str(e)}")
        return None


async def resolve_pending_search_parameters(
        unresolved_params: List[str],
        user_request: str,
        api: GbifApi,
        process: IChatBioAgentProcess,
) -> Tuple[Dict[str, List[int]], List[str]]:
    """
    Attempt to resolve clarification fields automatically.

    Args:
        unresolved_params: List of fields that need clarification
        user_request: Original user request
        api: GBIF API instance
        process: Process for logging

    Returns:
        Tuple of (resolved_fields_dict, remaining_unresolved_fields)
    """
    resolved = {}
    unresolved = []

    for field in unresolved_params:
        resolved_keys = await resolve_field_from_request(
            api, process, field, user_request
        )
        if resolved_keys:
            resolved[field] = resolved_keys
        else:
            unresolved.append(field)
            await process.log(f"Could not auto-resolve {field}")

    return resolved, unresolved


async def resolve_names_to_taxonkeys(
        api: GbifApi, organisms: List[IdentifiedOrganism], process: IChatBioAgentProcess
) -> list:
    """
    Resolve scientific names to GBIF taxon keys using the species match API.

    Note:
        This function uses the GBIF /v2/species/match endpoint for fuzzy name matching.
        Only successfully resolved names will have their taxon keys included in the result.
        Each API call generates an artifact for tracking purposes.
    """
    if not organisms:
        return []

    taxon_keys = []

    for organism in organisms:
        data = organism.model_dump(exclude_none=True, mode="json")
        await process.log(f"Resolving organism", data=data)
        result = None
        url = None
        name = data.get("scientific_name", None)
        rank = data.get("taxonomic_rank", None)
        if not name:
            await process.log(f"No scientific name found for organism: {data}")
            continue
        try:
            # Map rank names to GBIFSpeciesNameMatchParams parameter names
            rank_param_map = {
                "family": "family",
                "genus": "genus",
                "species": "scientificName",
                "order": "order",
                "class": "taxonomic_class",
                "phylum": "phylum",
                "kingdom": "kingdom",
            }
            params_dict = {}
            rank_field = (
                rank_param_map.get(rank.lower()) if isinstance(rank, str) else None
            )
            result = None
            url = None

            # Try with rank-specific parameter if available
            if rank_field:
                params_dict[rank_field] = name
                params = GBIFSpeciesNameMatchParams(**params_dict)
                url = api.build_species_match_url(params)
                await process.log(
                    f"Attempting to resolve {name} with rank {rank_field}",
                    data={"url": url},
                )
                result = await execute_request(url)

            # If no match found with rank-specific parameter, try with scientificName
            if not result or not (
                    result.get("usage") and result.get("usage", {}).get("key")
            ):
                params = GBIFSpeciesNameMatchParams(scientificName=name)
                url = api.build_species_match_url(params)
                await process.log(
                    f"Could not resolve to taxon key for {name} with rank {rank_field}, attempting to resolve with scientificName",
                    data={"url": url},
                )
                result = await execute_request(url)

            # If still no match, try with verbose=True to get alternatives
            if not result or not (
                    result.get("usage") and result.get("usage", {}).get("key")
            ):
                params = GBIFSpeciesNameMatchParams(scientificName=name, verbose=True)
                url = api.build_species_match_url(params)
                await process.log(
                    f"Could not resolve to taxon key for '{name}', trying alternate names with `verbose=true`",
                    data={"url": url},
                )
                data = await execute_request(url)
                alternatives = data.get("diagnostics", {}).get("alternatives", [])
                if alternatives:
                    # Format alternatives list
                    first_5 = alternatives[:5]
                    alternatives_text = f"Found {len(alternatives)} alternatives. Here are the first {len(first_5)}:\n\n"

                    for alt in first_5:
                        usage = alt.get("usage", {})
                        rank = usage.get("rank", "Unknown")
                        scientific_name = usage.get(
                            "name", usage.get("scientificName", "Unknown")
                        )

                        # Extract classification hierarchy
                        classification = alt.get("classification", [])
                        classification_names = [
                            item.get("name", "")
                            for item in classification
                            if item.get("name")
                        ]
                        classification_str = (
                            " | ".join(classification_names)
                            if classification_names
                            else ""
                        )

                        alternatives_text += f'- {rank} "{scientific_name}"'
                        if classification_str:
                            alternatives_text += (
                                f" with classification {classification_str}"
                            )
                        alternatives_text += "\n"

                    await process.log(alternatives_text)

                    # Use first alternative
                    first_alt = alternatives[0]
                    first_usage = first_alt.get("usage", {})
                    first_scientific_name = first_usage.get(
                        "name", first_usage.get("scientificName", "Unknown")
                    )
                    await process.log(f'Assuming option 1: "{first_scientific_name}"')
                    result = first_alt

            # generate artifact for the response
            if result.get("usage") and result.get("usage", {}).get("key"):
                taxon_key = result["usage"]["key"]
                taxon_keys.append(taxon_key)
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"GBIF Species Match API call results for: {name}",
                    uris=[url],
                    metadata={
                        "source": "GBIF",
                    },
                )
                continue
            else:
                await process.log(
                    f"No match or alternatives found for '{name}'",
                    data={
                        "source": "GBIF",
                        "api_url": url,
                    },
                )
                continue

        except Exception as e:
            await process.log(
                f"Failed to resolve name '{name}': {e}",
                data={
                    "source": f"GBIF",
                    "error": str(e),
                },
            )
            continue

    await process.log(f"Resolved {len(taxon_keys)} out of {len(organisms)} names.")
    return taxon_keys
