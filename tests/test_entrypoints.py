import pytest
from unittest.mock import patch
from ichatbio.agent_response import ArtifactResponse


@pytest.mark.asyncio
async def test_find_occurrence_records(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 10,
        "results": [{"key": 123, "scientificName": "Puma concolor"}],
        "facets": []
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(context, "Find Puma concolor", "find_occurrence_records", None)

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    # The agent first does species matching, so we need to check for that
    species_artifacts = [a for a in artifacts if a.metadata.get("data_source") == "GBIF Species Match"]
    assert species_artifacts, "Expected species match artifact"


@pytest.mark.asyncio
async def test_count_occurrence_records(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 0,
        "results": [],
        "facets": [{"field": "country", "counts": [{"name": "US", "count": 150}]}]
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(
            context, "Count Puma concolor by country", "count_occurrence_records", None
        )
    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    # The agent first does species matching, so we need to check for that
    species_artifacts = [a for a in artifacts if a.metadata.get("data_source") == "GBIF Species Match"]
    assert species_artifacts, "Expected species match artifact"


@pytest.mark.asyncio
async def test_find_occurrence_by_id(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 1,
        "results": [{"key": 1258202881, "scientificName": "Puma concolor"}],
        "facets": []
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(context, "Find occurrence 1258202881", "find_occurrence_by_id", None)

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    assert artifacts[0].metadata["data_source"] == "GBIF Occurrence"


@pytest.mark.asyncio
async def test_find_species_records(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 15,
        "results": [{"key": 123456789, "scientificName": "Panthera leo", "rank": "SPECIES"}],
        "facets": []
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(
            context,
            "Find lion (scientific name: Panthera leo)",
            "find_species_records",
            None,
        )

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    assert artifacts[0].metadata["data_source"] == "GBIF Species"


@pytest.mark.asyncio
async def test_count_species_records(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 0,
        "results": [],
        "facets": [{"field": "kingdom", "counts": [{"name": "Animalia", "count": 250}]}]
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(context, "Count species by kingdom", "count_species_records", None)

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    assert artifacts[0].metadata["data_source"] == "GBIF Species"


@pytest.mark.asyncio
async def test_find_species_taxonomic_information(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 1,
        "results": [{"key": 123456789, "scientificName": "Panthera leo"}],
        "facets": []
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(
            context,
            "Get taxonomy for Panthera leo",
            "find_taxonomic_information",
            None,
        )

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one artifact"


@pytest.mark.asyncio
async def test_find_datasets(agent, context, messages):
    mock_response = {
        "status_code": 200,
        "count": 25,
        "results": [{
            "key": "4fa7b334-ce0d-4e88-aaae-2e0c138d049e",
            "title": "iNaturalist Research-grade Observations",
            "type": "OCCURRENCE"
        }],
        "facets": []
    }

    with patch('src.gbif.fetch.execute_request') as mock_execute:
        mock_execute.return_value = mock_response
        await agent.run(context, "Find occurrence datasets", "find_datasets", None)

    artifacts = [m for m in messages if isinstance(m, ArtifactResponse)]
    assert artifacts, "Expected at least one ArtifactResponse"
    assert artifacts[0].metadata["data_source"] == "GBIF Registry"
