from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypeVar

from pydantic import BaseModel

from src.gbif.fetch import execute_request
from src.log import logger


VocabName = str
FieldName = str
NormalizedValue = str
T = TypeVar("T", bound=BaseModel)


VOCABULARY_FIELDS: Dict[FieldName, VocabName] = {
    "degreeOfEstablishment": "DegreeOfEstablishment",
    "establishmentMeans": "EstablishmentMeans",
    "pathway": "Pathway",
}

VOCABULARY_CACHE_TTL_SECONDS = 24 * 60 * 60
VOCABULARY_PAGE_SIZE = 100


@dataclass(frozen=True)
class NormalizationMatch:
    field_name: str
    original_value: str
    canonical_value: str
    vocabulary_name: str


@dataclass(frozen=True)
class NormalizationMiss:
    field_name: str
    original_value: str
    vocabulary_name: str


@dataclass
class NormalizationReport:
    matches: List[NormalizationMatch] = field(default_factory=list)
    misses: List[NormalizationMiss] = field(default_factory=list)
    vocabularies_used: List[str] = field(default_factory=list)


@dataclass
class _VocabularyCacheEntry:
    fetched_at: datetime
    canonical_map: Dict[str, str]
    display_names: Dict[str, str]


_VOCABULARY_CACHE: Dict[str, _VocabularyCacheEntry] = {}
_VOCABULARY_LOCKS: Dict[str, Lock] = defaultdict(Lock)


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    if hasattr(value, "value"):
        value = value.value

    text = str(value).strip().casefold()
    return "".join(char for char in text if char.isalnum())


def _split_phrase_tokens(value: Any) -> List[str]:
    if value is None:
        return []

    text = str(value).strip().casefold()
    tokens: List[str] = []
    current = []
    for char in text:
        if char.isalnum():
            current.append(char)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return [token for token in tokens if token]


def _expand_label_aliases(value: Any, max_window: int = 4) -> List[str]:
    tokens = _split_phrase_tokens(value)
    aliases: List[str] = []

    for start_index in range(len(tokens)):
        for end_index in range(start_index + 1, min(len(tokens), start_index + max_window) + 1):
            alias = "".join(tokens[start_index:end_index])
            if alias:
                aliases.append(alias)

    return aliases


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _build_concept_lookup(concepts: Iterable[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    canonical_map: Dict[str, str] = {}
    display_names: Dict[str, str] = {}

    for concept in concepts:
        canonical_value = concept.get("name")
        if not canonical_value:
            continue

        display_names[canonical_value] = canonical_value

        aliases = {canonical_value}
        for label in concept.get("label", []) or []:
            if isinstance(label, dict):
                label_value = label.get("value")
            else:
                label_value = label
            if label_value:
                aliases.add(label_value)
                aliases.update(_expand_label_aliases(label_value))

        for alias in aliases:
            normalized = _normalize_token(alias)
            if normalized:
                canonical_map[normalized] = canonical_value

    # Prefer the shortest canonical value when multiple aliases normalize to the same token.
    canonical_map = dict(sorted(canonical_map.items(), key=lambda item: (len(item[1]), item[1])))

    return canonical_map, display_names


async def _fetch_vocab_page(vocabulary_name: str, offset: int) -> Dict[str, Any]:
    url = (
        f"https://api.gbif.org/v1/vocabularies/{vocabulary_name}/concepts"
        f"?limit={VOCABULARY_PAGE_SIZE}&offset={offset}"
    )
    return await execute_request(url)


async def _fetch_vocabulary_concepts(vocabulary_name: str) -> List[Dict[str, Any]]:
    first_page = await _fetch_vocab_page(vocabulary_name, 0)
    concepts = list(first_page.get("results", []) or [])

    total_count = int(first_page.get("count", len(concepts)) or len(concepts))
    end_of_records = bool(first_page.get("endOfRecords", True))

    if end_of_records or len(concepts) >= total_count:
        return concepts

    offset = VOCABULARY_PAGE_SIZE
    while len(concepts) < total_count:
        page = await _fetch_vocab_page(vocabulary_name, offset)
        page_results = list(page.get("results", []) or [])
        if not page_results:
            break

        concepts.extend(page_results)
        offset += VOCABULARY_PAGE_SIZE

        if page.get("endOfRecords", False):
            break

    return concepts


async def _get_vocabulary_lookup(vocabulary_name: str) -> _VocabularyCacheEntry:
    now = datetime.now(timezone.utc)
    cache_entry = _VOCABULARY_CACHE.get(vocabulary_name)
    if cache_entry:
        age_seconds = (now - cache_entry.fetched_at).total_seconds()
        if age_seconds < VOCABULARY_CACHE_TTL_SECONDS:
            return cache_entry

    lock = _VOCABULARY_LOCKS[vocabulary_name]
    with lock:
        cache_entry = _VOCABULARY_CACHE.get(vocabulary_name)
        if cache_entry:
            age_seconds = (now - cache_entry.fetched_at).total_seconds()
            if age_seconds < VOCABULARY_CACHE_TTL_SECONDS:
                return cache_entry

    try:
        concepts = await _fetch_vocabulary_concepts(vocabulary_name)

        canonical_map, display_names = _build_concept_lookup(concepts)
        cache_entry = _VocabularyCacheEntry(
            fetched_at=now,
            canonical_map=canonical_map,
            display_names=display_names,
        )
        _VOCABULARY_CACHE[vocabulary_name] = cache_entry
        return cache_entry
    except Exception as exc:
        if cache_entry:
            logger.warning(
                "Using stale GBIF vocabulary cache for %s after fetch error: %s",
                vocabulary_name,
                exc,
            )
            return cache_entry
        raise


async def normalize_occurrence_params(params: T) -> Tuple[T, NormalizationReport]:
    """Normalize vocabulary-backed occurrence parameters to canonical GBIF concept names."""

    updates: Dict[str, Any] = {}
    report = NormalizationReport()

    for field_name, vocabulary_name in VOCABULARY_FIELDS.items():
        raw_value = getattr(params, field_name, None)
        if raw_value is None:
            continue

        lookup = await _get_vocabulary_lookup(vocabulary_name)
        report.vocabularies_used.append(vocabulary_name)

        normalized_values: List[str] = []
        for item in _as_list(raw_value):
            normalized_key = _normalize_token(item)
            canonical_value = lookup.canonical_map.get(normalized_key)
            if canonical_value:
                normalized_values.append(canonical_value)
                original_text = str(item)
                if original_text != canonical_value:
                    report.matches.append(
                        NormalizationMatch(
                            field_name=field_name,
                            original_value=original_text,
                            canonical_value=canonical_value,
                            vocabulary_name=vocabulary_name,
                        )
                    )
            else:
                normalized_values.append(str(item))
                report.misses.append(
                    NormalizationMiss(
                        field_name=field_name,
                        original_value=str(item),
                        vocabulary_name=vocabulary_name,
                    )
                )

        if isinstance(raw_value, list):
            updates[field_name] = normalized_values
        else:
            updates[field_name] = normalized_values[0] if normalized_values else raw_value

    if updates:
        params = params.model_copy(update=updates)

    return params, report


def clear_vocabulary_cache() -> None:
    """Helper used by tests to reset in-memory cache."""

    _VOCABULARY_CACHE.clear()
