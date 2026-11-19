import app_config
import instructor
from openai import AsyncOpenAI


async def get_client():
    llm_access = app_config.llm_access.get()
    return instructor.from_openai(
        AsyncOpenAI(base_url=llm_access.base_url, api_key=llm_access.api_key),
        model=app_config.settings().llm
    )
