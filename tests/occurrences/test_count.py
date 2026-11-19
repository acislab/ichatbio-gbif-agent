import pytest
from entrypoints import occurrences
from gbif.api import GbifApi


@pytest.mark.asyncio
async def test_resolve_keys_to_names():
    key_names = await occurrences.count.resolve_keys_to_names(GbifApi(), {"3PQ6", "8VRHY"})
    assert key_names == {"3PQ6": "Chylismia", "8VRHY": "Carex"}
