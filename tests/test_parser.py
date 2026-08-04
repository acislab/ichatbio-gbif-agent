import logging
from enum import Enum
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, Field
from pydantic import ValidationError

from src.gbif.parser import build_vocabulary_enum, create_response_model, parse
from src.models.entrypoints import GBIFOccurrenceSearchParams


class MockParameters(BaseModel):
    species: str = Field(default=None)
    country: str = Field(default=None)


@pytest.fixture
def mock_openai_response():
    return {
        "params": {"species": "Rattus rattus", "country": "US"},
        "artifact_description": "Species records for Rattus rattus in US",
        "clarification_needed": False,
        "clarification_reason": None,
    }


@pytest.mark.asyncio
async def test_create_response_model():
    ResponseModel = await create_response_model(MockParameters)
    assert "params" in ResponseModel.model_fields
    assert "artifact_description" in ResponseModel.model_fields
    assert "clarification_needed" in ResponseModel.model_fields
    assert "clarification_reason" in ResponseModel.model_fields
    instance = ResponseModel(
        plan="test plan",
        params=MockParameters(species="test"),
        artifact_description="test description",
        clarification_needed=False,
        clarification_reason=None,
    )
    assert instance.params.species == "test"
    assert instance.artifact_description == "test description"


@pytest.mark.asyncio
@patch("src.gbif.parser.get_client")
async def test_parse_success_and_message_structure(mock_get_client, mock_openai_response):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    mock_get_client.return_value = mock_client
    result = await parse(
        "find Rattus rattus in US", "find_occurrence_records", MockParameters
    )
    mock_client.chat.completions.create.assert_called_once()
    assert result == mock_openai_response
    mock_client.chat.completions.create.reset_mock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    await parse("find birds", "find_occurrence_records", MockParameters)
    messages = mock_client.chat.completions.create.call_args[1]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"].endswith("find birds")


@pytest.mark.asyncio
@patch("src.gbif.param_normalizer.execute_request")
async def test_build_vocabulary_enum_filters_deprecated_and_is_deterministic(
    mock_execute_request,
):
    async def fake_execute_request(url: str):
        if "offset=0" in url:
            return {
                "count": 4,
                "endOfRecords": False,
                "results": [
                    {"name": "beta-gamma"},
                    {"name": "Alpha Value"},
                    {"name": "deprecated thing", "deprecated": True},
                ],
            }
        if "offset=100" in url:
            return {
                "count": 4,
                "endOfRecords": True,
                "results": [{"name": "gamma"}],
            }
        raise AssertionError(f"Unexpected URL: {url}")

    mock_execute_request.side_effect = fake_execute_request

    enum_type = await build_vocabulary_enum("DegreeOfEstablishment")
    assert list(enum_type.__members__) == ["ALPHA_VALUE", "BETA_GAMMA", "GAMMA"]
    assert [member.value for member in enum_type] == [
        "Alpha Value",
        "beta-gamma",
        "gamma",
    ]

    second_enum_type = await build_vocabulary_enum("DegreeOfEstablishment")
    assert list(second_enum_type.__members__) == ["ALPHA_VALUE", "BETA_GAMMA", "GAMMA"]
    assert mock_execute_request.await_count == 4


@pytest.mark.asyncio
async def test_create_response_model_applies_live_vocabulary_constraint():
    degree_enum = Enum(
        "DegreeOfEstablishment",
        {"REPRODUCING": "reproducing", "ESTABLISHED": "established"},
        type=str,
    )
    establishment_enum = Enum(
        "EstablishmentMeans",
        {"NATIVE": "native", "INTRODUCED": "introducedAssistedColonisation"},
        type=str,
    )
    pathway_enum = Enum(
        "Pathway",
        {"AGRICULTURE": "Agriculture", "TRANSPORT": "Transport"},
        type=str,
    )

    async def fake_build_vocabulary_enum(vocabulary_name: str):
        mapping = {
            "DegreeOfEstablishment": degree_enum,
            "EstablishmentMeans": establishment_enum,
            "Pathway": pathway_enum,
        }
        return mapping[vocabulary_name]

    with patch("src.gbif.parser.build_vocabulary_enum", side_effect=fake_build_vocabulary_enum):
        response_model = await create_response_model(GBIFOccurrenceSearchParams)

    valid_instance = response_model.model_validate(
        {
            "plan": "Use invasive species vocabulary filters.",
            "params": {
                "degreeOfEstablishment": ["reproducing"],
                "establishmentMeans": ["native"],
                "pathway": ["Agriculture"],
            },
            "artifact_description": "Filtered records",
            "clarification_needed": False,
            "clarification_reason": None,
        }
    )
    assert valid_instance.params.degreeOfEstablishment[0].value == "reproducing"
    assert valid_instance.params.establishmentMeans[0].value == "native"
    assert valid_instance.params.pathway[0].value == "Agriculture"

    with pytest.raises(ValidationError):
        response_model.model_validate(
            {
                "plan": "Use invasive species vocabulary filters.",
                "params": {
                    "degreeOfEstablishment": ["not-allowed"],
                },
                "artifact_description": "Filtered records",
                "clarification_needed": False,
                "clarification_reason": None,
            }
        )


@pytest.mark.asyncio
async def test_create_response_model_degrades_to_unconstrained_on_vocab_failure(caplog):
    async def fake_execute_request(url: str):
        if "Pathway" in url:
            raise RuntimeError("GBIF unreachable")
        return {
            "count": 1,
            "endOfRecords": True,
            "results": [{"name": "native"}],
        }

    with patch("src.gbif.param_normalizer.execute_request", side_effect=fake_execute_request):
        caplog.set_level(logging.WARNING, logger="gbif.agent")
        response_model = await create_response_model(GBIFOccurrenceSearchParams)

    assert "Pathway" in caplog.text
    unconstrained_instance = response_model.model_validate(
        {
            "plan": "Fallback to unconstrained model.",
            "params": {
                "degreeOfEstablishment": ["anything-goes"],
                "establishmentMeans": ["still-allowed"],
                "pathway": ["whatever"],
            },
            "artifact_description": "Fallback records",
            "clarification_needed": False,
            "clarification_reason": None,
        }
    )
    assert unconstrained_instance.params.degreeOfEstablishment == ["anything-goes"]
    assert unconstrained_instance.params.establishmentMeans == ["still-allowed"]
    assert unconstrained_instance.params.pathway == ["whatever"]
