from typing import Any, Optional
from typing_extensions import override

from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext
from ichatbio.types import AgentCard
from pydantic import BaseModel

from src.entrypoints import occurrences, species, registry
from src.instructor_client import update_llm_credentials
from src.log import logger


class GBIFAgent(IChatBioAgent):
    @override
    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            name="GBIF Search",
            description="Searches for information in the GBIF portal (https://gbif.org).",
            icon='data:image/svg+xml;utf8,<svg viewBox="90 239.1 539.7 523.9" xmlns="http://www.w3.org/2000/svg" fill="rgb(34,197,94)"><path d="M325.5,495.4c0-89.7,43.8-167.4,174.2-167.4C499.6,417.9,440.5,495.4,325.5,495.4"/><path d="M534.3,731c24.4,0,43.2-3.5,62.4-10.5c0-71-42.4-121.8-117.2-158.4c-57.2-28.7-127.7-43.6-192.1-43.6c28.2-84.6,7.6-189.7-19.7-247.4c-30.3,60.4-49.2,164-20.1,248.3c-57.1,4.2-102.4,29.1-121.6,61.9c-1.4,2.5-4.4,7.8-2.6,8.8c1.4,0.7,3.6-1.5,4.9-2.7c20.6-19.1,47.9-28.4,74.2-28.4c60.7,0,103.4,50.3,133.7,80.5C401.3,704.3,464.8,731.2,534.3,731"/></svg>',
            entrypoints=[
                occurrences.search.entrypoint,
                occurrences.count.entrypoint,
                species.search.entrypoint,
                species.count.entrypoint,
                species.search_taxa.entrypoint,
                occurrences.search_by_id.entrypoint,
                registry.search.entrypoint,
            ],
        )

    @override
    async def run(
        self,
        context: ResponseContext,
        request: str,
        entrypoint: str,
        params: Optional[BaseModel],
        metadata: dict[str, Any] | None = None,
    ):
        update_llm_credentials(metadata)
        logger.info(f"AGENT | Entrypoint={entrypoint} | Request={request}")
        if params:
            logger.info(f"AGENT | Received params: {params}")
        try:
            match entrypoint:
                case occurrences.search.entrypoint.id:
                    await occurrences.search.run(context, request)
                case occurrences.count.entrypoint.id:
                    await occurrences.count.run(context, request)
                case species.search.entrypoint.id:
                    await species.search.run(context, request)
                case species.count.entrypoint.id:
                    await species.count.run(context, request)
                case species.search_taxa.entrypoint.id:
                    await species.search_taxa.run(context, request)
                case occurrences.search_by_id.entrypoint.id:
                    await occurrences.search_by_id.run(context, request)
                case registry.search.entrypoint.id:
                    await registry.search.run(context, request)
                case _:
                    error_msg = f"Unknown entrypoint: {entrypoint}"
                    logger.error(f"AGENT_ERROR | {error_msg}")
                    raise ValueError(error_msg)

        except Exception as e:
            logger.error(
                f"AGENT_ERROR | Entrypoint={entrypoint} | Error={type(e).__name__}: {str(e)}"
            )
            raise
