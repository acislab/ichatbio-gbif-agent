import pytest
from pydantic import BaseModel

from src.gbif.param_normalizer import clear_vocabulary_cache, normalize_occurrence_params


class LocalOccurrenceParams(BaseModel):
    establishmentMeans: list[str] | None = None
    degreeOfEstablishment: list[str] | None = None
    pathway: list[str] | None = None


@pytest.fixture(autouse=True)
def reset_vocab_cache():
    clear_vocabulary_cache()
    yield
    clear_vocabulary_cache()


@pytest.mark.asyncio
async def test_normalizer_canonicalizes_establishment_vocabularies(monkeypatch):
    calls = []

    async def fake_execute_request(url):
        calls.append(url)
        if "EstablishmentMeans" in url:
            return {
                "count": 1,
                "endOfRecords": True,
                "results": [
                    {
                        "name": "introducedAssistedColonisation",
                        "label": [
                            {"value": "Introduced (Assisted colonisation)"}
                        ],
                    }
                ],
            }
        if "DegreeOfEstablishment" in url:
            return {
                "count": 2,
                "endOfRecords": True,
                "results": [
                    {"name": "reproducing", "label": [{"value": "Reproducing"}]},
                    {"name": "established", "label": [{"value": "Established"}]},
                ],
            }
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("src.gbif.param_normalizer.execute_request", fake_execute_request)

    params = LocalOccurrenceParams(
        establishmentMeans=["AssistedColonisation"],
        degreeOfEstablishment=["Reproducing", "Established"],
    )

    normalized, report = await normalize_occurrence_params(params)

    assert normalized.establishmentMeans == ["introducedAssistedColonisation"]
    assert normalized.degreeOfEstablishment == ["reproducing", "established"]
    assert len(report.matches) == 3
    assert report.misses == []
    assert sorted(report.vocabularies_used) == ["DegreeOfEstablishment", "EstablishmentMeans"]
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_normalizer_reuses_cache(monkeypatch):
    calls = []

    async def fake_execute_request(url):
        calls.append(url)
        return {
            "count": 1,
            "endOfRecords": True,
            "results": [
                {
                    "name": "introducedAssistedColonisation",
                    "label": [{"value": "Introduced (Assisted colonisation)"}],
                }
            ],
        }

    monkeypatch.setattr("src.gbif.param_normalizer.execute_request", fake_execute_request)

    params = LocalOccurrenceParams(
        establishmentMeans=["AssistedColonisation"],
    )

    first_normalized, first_report = await normalize_occurrence_params(params)
    second_normalized, second_report = await normalize_occurrence_params(params)

    assert first_normalized.establishmentMeans == ["introducedAssistedColonisation"]
    assert second_normalized.establishmentMeans == ["introducedAssistedColonisation"]
    assert len(first_report.matches) == 1
    assert len(second_report.matches) == 1
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_normalizer_keeps_unknown_values(monkeypatch):
    async def fake_execute_request(url):
        return {
            "count": 1,
            "endOfRecords": True,
            "results": [
                {
                    "name": "otherTransport",
                    "label": [{"value": "Other means of transport"}],
                }
            ],
        }

    monkeypatch.setattr("src.gbif.param_normalizer.execute_request", fake_execute_request)

    params = LocalOccurrenceParams(
        pathway=["MadeUpPathway"],
    )

    normalized, report = await normalize_occurrence_params(params)

    assert normalized.pathway == ["MadeUpPathway"]
    assert len(report.matches) == 0
    assert len(report.misses) == 1
    assert report.misses[0].original_value == "MadeUpPathway"
