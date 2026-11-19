from typing import List, Optional

from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import AgentEntrypoint
from models.base import ProductionBaseModel
from models.entrypoints import GBIFSpeciesTaxonomicParams
from pydantic import BaseModel, Field
from src.enums.species import (
    TaxonomicStatusEnum,
    TaxonomicRankEnum,
    QueryFieldEnum,
)
from src.gbif.api import GbifApi
from src.gbif.parser import parse
from src.instructor_client import get_client
from src.log import with_logging
from src.models.entrypoints import GBIFSpeciesSearchParams

description = f"""
**Use Case:** Use this entrypoint to retrieve taxonomic information (like the full parent hierarchy, child taxa, or synonyms) that matches with a scientificName or taxonKey. It can also be used to find specific identifiers such as taxonKey, kingdomKey, etc in GBIF Backbone Taxonomy.

**Triggers On:** User requests may ask to find, get, or show the "taxonomic information of", "synonyms of", "children of", "parents of", "kingdomKey/taxonKey/classKey...etc" for a taxon.

**Key Inputs:** Requires a taxonKey or a scientificName. It also accepts a rank and a qField to narrow down the search results if the user provides a name; Make sure to include the fields in the request.

If only name is provided, it will try to first search for the taxon usageKey in the GBIF Backbone Taxonomy and then retrieve the taxonomic information. If a taxonKey is provided, it will directly retrieve the taxonomic information.
"""

entrypoint = AgentEntrypoint(
    id="find_taxonomic_information",
    description=description
)

GBIF_BACKBONE_DATASET_KEY = "d7dddbf4-2cf0-4f39-9b2a-bb099caae36c"


class TaxonLookupParameters(ProductionBaseModel):
    """Search parameters for retrieving taxonomic records from GBIF"""

    taxon_key: Optional[str] = Field(
        None,
        description="A CoL XR taxon ID",
        examples=["Q2M4", "P", "623RM"],
    )

    taxon_name: Optional[str] = Field(
        None,
        description="The scientific name or vernacular name of the taxon",
        examples=["Panthera onca", "jaguar", "Quercus robur", "oak tree"],
    )


@with_logging("find_taxonomic_information")
async def run(context: ResponseContext, request: str):
    """Retrieves comprehensive taxonomic information by taxon ID."""

    async with context.begin_process("Searching GBIF for taxonomic records") as process:
        await process.log("Generating search parameters...")
        response = await parse(request, entrypoint.id, GBIFSpeciesTaxonomicParams)
        if response.clarification_needed:
            await process.log(f"Clarification needed: {response.clarification_reason}")
            return

        params: GBIFSpeciesTaxonomicParams = response.params
        api = GbifApi()

        await process.log("Generated search parameters", data=params.model_dump(exclude_defaults=True))

        if not params.key and not params.name:
            await context.reply("Taxon key or name is required to retrieve taxonomic information.")
            return

        if not params.key:
            await process.log(f"No taxon key found, searching by name: {params.name}")
            taxon_key = await _find_taxon_by_name(api, request, params.name, params.rank, params.qField, process)
            params.key = taxon_key

        url = api.build_species_key_search_url(params.key)

        try:
            await process.log(f"Sending GET request to {url}")
            result = await api.get(url)

            await process.create_artifact(
                mimetype=result.headers.get("content-type", "application/json"),
                description=response.artifact_description,
                uris=[url],
                content=result.content,
                metadata={"source": "GBIF"},
            )

        except Exception as e:
            await process.log(f"Error retrieving taxonomic information", data={"error": str(e)})
            await context.reply(f"Failed to retrieve taxonomic information: {str(e)}")


class TaxonMatch(BaseModel):
    key: str
    scientificName: str
    canonicalName: Optional[str] = None
    rank: Optional[str] = None
    kingdom: Optional[str] = None
    phylum: Optional[str] = None
    class_: Optional[str] = Field(None, alias="class")
    order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    isExtinct: Optional[bool] = None


async def _find_taxon_by_name(
        api: GbifApi,
        user_query: str,
        name: str,
        rank: Optional[TaxonomicRankEnum],
        q_field: Optional[QueryFieldEnum],
        process: IChatBioAgentProcess,
) -> str:
    await process.log(f"Searching for taxon by name: \"{name}\"")
    params = GBIFSpeciesSearchParams(
        q=name,
        status=TaxonomicStatusEnum.ACCEPTED,
        datasetKey=GBIF_BACKBONE_DATASET_KEY,
        rank=rank,
        qField=q_field,
    )

    url = api.build_species_search_url(params)
    await process.log(f"Sending GET request to {url}")

    try:
        response = (await api.get(url)).json()
        records = response.get("results", [])
        count = response.get("count", 0)
        await process.log(f"The API returned {len(records)} of {count} taxon matches for \"{name}\"")

        taxon_matches = [
            TaxonMatch(
                key=r.get("taxonID"),
                scientificName=r.get("scientificName"),
                canonicalName=r.get("canonicalName"),
                rank=r.get("rank"),
                kingdom=r.get("kingdom"),
                phylum=r.get("phylum"),
                class_=r.get("class"),
                order=r.get("order"),
                family=r.get("family"),
                genus=r.get("genus"),
                isExtinct=r.get("isExtinct"),
            )
            for r in records
        ]

        if not taxon_matches:
            raise ValueError(f"No taxon matches found for name: {name}")

        await process.create_artifact(
            mimetype="application/json",
            description=f"Taxon records matched to {name}",
            uris=[url],
            metadata={
                "source": "GBIF",
            },
        )

        best_match = await _find_best_taxon_match(taxon_matches, user_query)
        await process.log(f"Selected best match: {best_match.model_dump_json()}")
        return best_match.key

    except Exception as e:
        await process.log(f"Error while searching for taxon by name", data={"error": str(e), "taxon_name": name})
        raise


async def _find_best_taxon_match(
        taxon_matches: List[TaxonMatch], user_query: str
) -> TaxonMatch:
    client = await get_client()

    response = await client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a helpful biodiversity researcher assistant that finds the best match for a taxon name for the user query. You will be given a user query and a dictionary of taxon keys and details. You will need to return the best match.",
            },
            {
                "role": "user",
                "content": f"User query: {user_query}\n\nTaxon name to key: {taxon_matches}",
            },
        ],
        response_model=TaxonMatch,
    )

    return response
