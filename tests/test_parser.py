import pytest
from unittest.mock import patch, AsyncMock
from pydantic import BaseModel, Field
from src.gbif.parser import parse, create_response_model


class MockParameters(BaseModel):
    species: str = Field(default=None)
    country: str = Field(default=None)


@pytest.fixture
def mock_openai_response():
    return {
        "search_parameters": {"species": "Rattus rattus", "country": "US"},
        "artifact_description": "Species records for Rattus rattus in US",
        "clarification_needed": False,
        "clarification_reason": None,
    }


def test_create_response_model():
    ResponseModel = create_response_model(MockParameters)
    assert "params" in ResponseModel.model_fields
    assert "artifact_description" in ResponseModel.model_fields
    assert "clarification_needed" in ResponseModel.model_fields
    assert "clarification_reason" in ResponseModel.model_fields
    instance = ResponseModel(
        plan="Do it right!",
        params=MockParameters(species="test"),
        artifact_description="test description",
        clarification_needed=False,
        clarification_reason=None,
    )
    assert instance.params.species == "test"
    assert instance.artifact_description == "test description"


@pytest.mark.asyncio
@patch("instructor.from_provider")
async def test_parse_handles_api_error(mock_instructor):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mock_instructor.return_value = mock_client
    with pytest.raises(Exception, match="API Error"):
        await parse("test", "find_occurrence_records", MockParameters)


@pytest.mark.asyncio
@patch("instructor.from_provider")
async def test_parse_success_and_message_structure(
    mock_instructor, mock_openai_response
):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    mock_instructor.return_value = mock_client
    result = await parse(
        "find Rattus rattus in US", "find_occurrence_records", MockParameters
    )
    mock_client.chat.completions.create.assert_called_once()
    assert result == mock_openai_response
    mock_client.chat.completions.create.reset_mock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    await parse("find birds", "find_occurrence_records", MockParameters)
    messages = mock_client.chat.completions.create.call_args[1]["messages"]
    assert messages == [
        {"role": "system", "content": messages[0]["content"]},
        {"role": "user", "content": "find birds"},
    ]
