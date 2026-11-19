import pytest
from agent import GBIFAgent
from app_config import reload
from dotenv import load_dotenv

load_dotenv()
reload()


@pytest.fixture(scope="function")
def agent():
    return GBIFAgent()
