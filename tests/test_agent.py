from unittest.mock import AsyncMock, patch

import pytest


def test_get_agent_card(agent):
    card = agent.get_agent_card()

    assert card.name == "GBIF Search"
    assert len(card.entrypoints) == 7


@pytest.mark.asyncio
@patch("entrypoints.occurrences.search.run")
async def test_routes_to_correct_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "find_occurrence_records", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.occurrences.count.run")
async def test_routes_count_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "count_occurrence_records", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.occurrences.search_by_id.run")
async def test_routes_find_occurrence_by_id_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "find_occurrence_by_id", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.species.search.run")
async def test_routes_find_species_records_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "find_species_records", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.species.count.run")
async def test_routes_count_species_records_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "count_species_records", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.species.search_taxa.run")
async def test_routes_find_species_taxonomic_information_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "find_taxonomic_information", None)
    mock_run.assert_called_once_with(context, "test")


@pytest.mark.asyncio
@patch("entrypoints.registry.search.run")
async def test_routes_find_datasets_entrypoint(mock_run, agent, context):
    mock_run.return_value = AsyncMock()
    await agent.run(context, "test", "find_datasets", None)
    mock_run.assert_called_once_with(context, "test")
