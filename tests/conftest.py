import pytest
from app_config import reload
from dotenv import load_dotenv

from src.agent import GBIFAgent

load_dotenv()
reload()


@pytest.fixture(scope="function")
def agent():
    return GBIFAgent()
