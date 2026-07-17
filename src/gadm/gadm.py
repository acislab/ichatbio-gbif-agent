import asyncio
import os
import sqlite3
from typing import List, Optional, Tuple

from ichatbio.agent_response import IChatBioAgentProcess

from src.log import logger
from src.models.location import (
    Location,
    GADMHierarchy,
    GADMHierarchyLevel,
    GADMMatch,
    GadmMatchType,
    ResolvedLocation,
)

HERE = os.path.dirname(os.path.abspath(__file__))
GADM_GPKG_PATH = os.path.join(HERE, "gadm.gpkg")


def _open_gadm_connection(trace: bool = False) -> sqlite3.Connection:
    """Open read-only connection to GADM GeoPackage database."""
    if not os.path.exists(GADM_GPKG_PATH):
        raise FileNotFoundError(f"GADM file not found: {GADM_GPKG_PATH}")

    conn = sqlite3.connect(f"file:{GADM_GPKG_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    if trace:
        conn.set_trace_callback(print)

    return conn


def _get_feature_layers(conn: sqlite3.Connection) -> List[str]:
    """Retrieve all feature table names from the GeoPackage."""
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM gpkg_contents WHERE data_type = 'features'")
    return [row[0] for row in cur.fetchall()]


def _get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    """Retrieve column names for a specific table."""
    cur = conn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in cur.fetchall()]


def _build_name_match_clause(
    level: int, place_name: str, cols: List[str]
) -> Tuple[str, List[str]]:
    """
    Build SQL WHERE clause for matching place name at a specific GADM level.

    Searches across NAME_n, VARNAME_n, and NL_NAME_n columns using
    case-insensitive exact matching.

    Args:
        level: GADM level (0-3)
        place_name: Name to search for
        cols: Available columns in the table

    Returns:
        Tuple of (SQL clause, parameter list)
    """
    name_cols = [
        c
        for c in cols
        if c in [f"NAME_{level}", f"VARNAME_{level}", f"NL_NAME_{level}"]
    ]

    if not name_cols:
        return "1=0", []  # No name columns for this level

    predicates = [f'UPPER("{col}") = UPPER(?)' for col in name_cols]
    params = [place_name] * len(name_cols)

    return f"({' OR '.join(predicates)})", params


def _build_parent_constraint_clause(
    level: int, parent_gid: Optional[str], cols: List[str]
) -> Tuple[str, List[str]]:
    """
    Build SQL WHERE clause for parent GID constraint.

    Args:
        level: Current GADM level
        parent_gid: Parent's GID to constrain by
        cols: Available columns in the table

    Returns:
        Tuple of (SQL clause, parameter list), or ("1=1", []) if no constraint
    """
    if not parent_gid or level == 0:
        return "1=1", []

    parent_col = f"GID_{level - 1}"
    if parent_col not in cols:
        # Parent column doesn't exist - signal no match possible
        return "1=0", []

    return f'"{parent_col}" = ?', [parent_gid]


def _build_hierarchy_from_row(row: sqlite3.Row, max_level: int) -> GADMHierarchy:
    """
    Extract GADM hierarchy from a database row.

    Args:
        row: Database row containing GADM data
        max_level: Maximum level to extract (inclusive)

    Returns:
        GADMHierarchy object with levels 0 through max_level
    """
    row_dict = dict(row)
    levels_kwargs = {}

    # Our hierarchy model supports levels 0..3
    for level in range(min(max_level, 3) + 1):
        name = row_dict.get(f"NAME_{level}")
        gid = row_dict.get(f"GID_{level}")
        if name or gid:
            levels_kwargs[f"level_{level}"] = GADMHierarchyLevel(
                name=name,
                gid=gid if gid else None,
            )

    return GADMHierarchy(**levels_kwargs)


def _find_place_in_layer(
    conn: sqlite3.Connection,
    layer: str,
    level: int,
    place_name: str,
    parent_gid: Optional[str] = None,
    query_trace: Optional[List[str]] = None,
) -> Optional[sqlite3.Row]:
    """
    Search for a place in a specific GADM layer at a given level.

    Uses exact name matching with optional parent GID constraint for
    hierarchical filtering.

    Args:
        conn: Database connection
        layer: GADM layer (table) name
        level: GADM level (0=country, 1=state, 2=county, 3=locality)
        place_name: Name to search for
        parent_gid: Optional parent's GID for hierarchical constraint
        query_trace: Optional list to append executed SQL queries to

    Returns:
        Database row if found, None otherwise
    """
    cols = _get_table_columns(conn, layer)

    # Build WHERE clause components
    name_clause, name_params = _build_name_match_clause(level, place_name, cols)
    parent_clause, parent_params = _build_parent_constraint_clause(
        level, parent_gid, cols
    )

    # Check if search is viable
    if name_clause == "1=0" or parent_clause == "1=0":
        return None

    # Construct and execute query
    where_sql = f"{name_clause} AND {parent_clause}"
    sql = f'SELECT * FROM "{layer}" WHERE {where_sql} LIMIT 1'
    params = name_params + parent_params

    # Log query for debugging
    if query_trace is not None:
        query_str = sql
        for param in params:
            query_str = query_str.replace('?', f"'{param}'", 1)
        query_trace.append(query_str)

    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()

    if not row:
        return None

    # Validate that the matched row has a GID for this level
    row_dict = dict(row)
    gid = row_dict.get(f"GID_{level}")
    if not gid:
        return None

    return row


def _find_place_across_layers(
    conn: sqlite3.Connection,
    layers: List[str],
    level: int,
    place_name: str,
    parent_gid: Optional[str] = None,
    query_trace: Optional[List[str]] = None,
) -> Optional[sqlite3.Row]:
    """
    Search for a place across all GADM layers at a given level.

    Tries each layer until a match is found.

    Args:
        conn: Database connection
        layers: List of layer names to search
        level: GADM level to search at
        place_name: Name to search for
        parent_gid: Optional parent GID constraint
        query_trace: Optional query trace list

    Returns:
        First matching row found, or None
    """
    for layer in layers:
        row = _find_place_in_layer(
            conn, layer, level, place_name, parent_gid, query_trace
        )
        if row:
            return row

    return None


def _create_match_result(
    achieved_level: Optional[int],
    achieved_row: Optional[sqlite3.Row],
    expected_level: int,
    query_trace: List[str],
) -> GADMMatch:
    """
    Create a GADMMatch result from the matching process.

    Args:
        achieved_level: Deepest level successfully matched
        achieved_row: Database row for the achieved level
        expected_level: Most specific level that was requested
        query_trace: List of executed SQL queries

    Returns:
        GADMMatch with appropriate match type and hierarchy
    """
    if achieved_level is None or achieved_row is None:
        return GADMMatch(
            match_type=GadmMatchType.NONE,
            gadm_hierarchy=None,
            query_trace=query_trace,
        )

    hierarchy = _build_hierarchy_from_row(achieved_row, max_level=achieved_level)
    match_type = (
        GadmMatchType.COMPLETE
        if achieved_level == expected_level
        else GadmMatchType.PARTIAL
    )

    return GADMMatch(
        match_type=match_type,
        gadm_hierarchy=hierarchy,
        query_trace=query_trace,
    )


def perform_match(location: Location, trace: bool = False) -> GADMMatch:
    """
    Resolve a location address to GADM identifiers using hierarchical narrowing.

    Strategy:
        1. Start from least specific level (country)
        2. Find exact match and extract its GID
        3. Use that GID to constrain search at next level (state)
        4. Continue down the hierarchy to most specific level

    Example:
        Location(country="USA", state="Florida", county="Alachua")

        Step 1: Find USA → GID_0 = "USA"
        Step 2: Find Florida WHERE GID_0 = "USA" → GID_1 = "USA.11_1"
        Step 3: Find Alachua WHERE GID_1 = "USA.11_1" → GID_2 = "USA.11.1_1"

    Args:
        location: Location with hierarchy to resolve
        trace: Enable SQL query tracing to stderr (for debugging)

    Returns:
        GADMMatch with the deepest level successfully matched.
        Match type indicates COMPLETE if all levels matched, PARTIAL if some matched,
        or NONE if no match found. The query_trace contains all executed SQL.
    """
    conn = _open_gadm_connection(trace=trace)
    try:
        # Get available layers and prepare hierarchy
        layers = _get_feature_layers(conn)
        original_hierarchy = location.get_hierarchy()
        query_trace = []

        if not original_hierarchy:
            return GADMMatch(
                match_type=GadmMatchType.NONE,
                gadm_hierarchy=None,
                query_trace=query_trace,
            )

        # Reverse hierarchy to search from least to most specific
        # Original: [(3, 'locality', 'X'), (2, 'county', 'Y'), (1, 'state', 'Z'), (0, 'country', 'W')]
        # Reversed: [(0, 'country', 'W'), (1, 'state', 'Z'), (2, 'county', 'Y'), (3, 'locality', 'X')]
        hierarchy = list(reversed(original_hierarchy))

        # Track progress through hierarchy
        current_parent_gid = None
        achieved_level: Optional[int] = None
        achieved_row: Optional[sqlite3.Row] = None

        # Iteratively narrow search through each hierarchy level
        for level, level_name, place_name in hierarchy:
            # Skip continent level (not in GADM)
            if level_name == "continent":
                continue

            # Search across all layers for this level
            matched_row = _find_place_across_layers(
                conn, layers, level, place_name, current_parent_gid, query_trace
            )

            if not matched_row:
                # No match found - stop here and return what we have
                break

            # Update tracking for next iteration
            achieved_level = level
            achieved_row = matched_row
            current_parent_gid = dict(matched_row).get(f"GID_{level}")

        # Build final result
        expected_level = original_hierarchy[0][0]  # Most specific level requested
        return _create_match_result(
            achieved_level, achieved_row, expected_level, query_trace
        )

    finally:
        conn.close()


async def map_locations_to_gadm(
    locations: list[Location],
    process: IChatBioAgentProcess | None = None,
) -> list[ResolvedLocation]:
    # emit a process log to keep the stream alive during long silent GADM lookups (e.g. many coastal states).
    matched_locations: list[ResolvedLocation] = []
    total = len(locations)
    for i, loc in enumerate(locations, start=1):
        label = loc.state or loc.country or str(loc)
        if process:
            await process.log(f"Resolving location {i}/{total}: {label}")
        try:
            gadm_match: GADMMatch = await asyncio.to_thread(perform_match, loc, False)
            resolved = ResolvedLocation(**loc.model_dump(), **gadm_match.model_dump())
            if gadm_match.match_type == GadmMatchType.NONE:
                logger.warning(f"GADM | Location not found: {loc}")
            else:
                logger.info(f"GADM | Resolved {loc} → {gadm_match.match_type}")

            matched_locations.append(resolved)
        except Exception as e:
            logger.error(f"GADM | Error validating {loc}: {str(e)}")
            matched_locations.append(
                ResolvedLocation(
                    **loc.model_dump(),
                    **GADMMatch(match_type=GadmMatchType.NONE).model_dump(),
                )
            )

    return matched_locations


def serialize_locations(locations: list[ResolvedLocation]) -> list[dict]:
    """Serialize resolved locations to flat JSON-serializable dicts."""
    return [loc.model_dump(exclude_none=True, mode="json") for loc in locations]
