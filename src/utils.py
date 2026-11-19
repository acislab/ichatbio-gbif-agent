import dataclasses
import json
from importlib import resources

from instructor_client import get_client
from log import logger
from models.bionomia import BionomiaNameRecord, NameMatchResult
from models.location import Location
from pydantic import BaseModel, Field, model_validator, ConfigDict
from util_types import ParameterEnum


class NamedEntityType(ParameterEnum):
    PERSON = "person"
    PUBLISHING_ORGANIZATION = "publishing_organization"
    INSTITUTION = "institution"
    MUSEUM = "museum"
    COLLECTION = "collection"
    OTHER = "other"


class NamedEntity(BaseModel):
    """
    A named entity is a person, organization, or other entity that is found in the user request.
    """

    model_config = ConfigDict(extra="allow")
    type: NamedEntityType
    value: str = Field(description="The value of the entity")
    strict: bool = Field(
        description="True if the entity is a strict match; A strict match is when the value is enclosed in quotes like '\"John Doe\"'. in the user request.",
        default=False
    )
    type_if_other: str = Field(description="The type of the entity if it is OTHER")

    @model_validator(mode="after")
    def validate_named_entity_type_and_value(self):
        if self.type == NamedEntityType.OTHER:
            if not self.type_if_other:
                raise ValueError("type_if_other is required if type is OTHER")
            if not isinstance(self.value, str):
                raise ValueError("value must be a string if type is OTHER")
        return self


class IdentifiedOrganism(BaseModel):
    term_found: str = Field(
        description="The exact organism term as found in the user request (e.g., 'birds', 'monkey', 'Cercopithecidae')"
    )
    is_already_scientific: bool = Field(
        description="True if the term is already in scientific nomenclature, False if it's a common name"
    )
    scientific_name: str = Field(
        description="The scientific name (same as term_found if already scientific, or the translation if common name)"
    )
    taxonomic_rank: str = Field(
        description="The taxonomic rank of the scientific name (e.g., 'species', 'genus', 'family', 'order', 'class')"
    )


class UserRequestExpansion(BaseModel):
    reasoning: str = Field(
        description="Briefly describe: What organism terms found? What locations found? Any translations needed?"
    )
    organisms: list[IdentifiedOrganism] = Field(
        description="All organism terms found with their scientific names and taxonomic ranks",
        default_factory=list
    )
    locations: list[Location] = Field(
        description="All location references found with their types and names",
        default_factory=list
    )
    entities: list[NamedEntity] = Field(
        description="All named entities found with their types and values",
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_unique_scientific_names(self):
        organisms = self.organisms
        seen = set()
        for org in organisms:
            sci_name = org.scientific_name
            if sci_name:
                if sci_name.lower() in seen:
                    raise ValueError(
                        f"Duplicate scientific_name found in organisms: '{sci_name}'. Each scientific_name must be unique."
                    )
                seen.add(sci_name.lower())
        return self


def serialize_for_log(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump(exclude_defaults=True, mode="json")
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    return str(obj)


async def _generate_resolution_message(
        user_request: str,
        response: BaseModel,
        resolved_fields: dict,
        unresolved_fields: list,
) -> str:
    class ResolutionMessage(BaseModel):
        message: str = Field(
            ...,
            description="a brief message to clarify the search parameters",
        )

    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that crafts a brief message (don't make it an email) to clarify the search parameters. Include what were you able to resolve and what you still need to clarify. It should be a complete sentence.",
            },
            {
                "role": "user",
                "content": f"Generate the message for:\nUser request: {user_request}\nParsed Response: {json.dumps(serialize_for_log(response))}\nResolved fields: {resolved_fields}\nUnresolved fields: {unresolved_fields}.",
            },
        ]
        client = await get_client()
        response = await client.chat.completions.create(
            messages=messages,
            response_model=ResolutionMessage,
            max_tokens=100,
            temperature=0.2,
        )
        message_content = response.message
        return message_content

    except Exception as e:
        logger.error(
            f"LLM extraction failed, falling back to default message: {str(e)}"
        )
        return "I encountered an error while trying to generate a message about the clarification required from the user about their search."


async def _generate_artifact_description(details: str) -> str:
    class ArtifactDescription(BaseModel):
        description: str | None = Field(
            description="A concise characterization of the retrieved record statistics.",
            examples=[
                "Occurrence records for species Rattus rattus across multiple countries.",
                "Species-level record counts for observations created in 2025.",
                "Occurrence data for Psittacidae in Alaska, United States.",
                "Per-species record counts for records created in 2025",
            ],
            default=None,
        )

    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that summarizes GBIF API search parameters "
                    "into a short, meaningful English description. "
                    "Your output must be a single complete sentence summarizing the type of data retrieved. "
                    "Identify what kind of records (e.g., occurrence records, species counts), "
                    "and mention geographic or taxonomic filters when present. "
                    "Avoid repeating raw parameter names or producing fragments like 'per-country' "
                    "unless multiple countries are explicitly listed."
                ),
            },
            {
                "role": "user",
                "content": f"Generate a clear, natural-language description for this GBIF API request: \nDetails: {details}",
            },
        ]
        client = await get_client()
        response = await client.chat.completions.create(
            messages=messages,
            response_model=ArtifactDescription,
            max_tokens=60,
            temperature=0.2,
        )
        message_content = response.description
        return message_content
    except Exception as e:
        logger.error(
            f"LLM extraction failed, falling back to default description: {str(e)}"
        )
        return "I encountered an error while trying to generate a description of the artifact."


def serialize_organisms(organisms: list) -> list:
    return [org.model_dump(exclude_none=True, mode="json") for org in organisms]


def serialize_entities(entities: list) -> list:
    return [entity.model_dump(exclude_none=True, mode="json") for entity in entities]


async def _preprocess_user_request(user_request: str):
    """
    Translates organism-related terms in user request to scientific nomenclature
    and extracts location information.
    """
    system_prompt = resources.read_text("resources.prompts", "preprocess_request.md")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"User request: {user_request}"},
    ]

    client = await get_client()
    response = await client.chat.completions.create(
        messages=messages,
        response_model=UserRequestExpansion,
        max_retries=2
    )

    logger.info(
        f"Identified organisms and locations: {response.model_dump(exclude_none=True)}"
    )
    return response


class MatchSelection(BaseModel):
    """A selected match identified by its match_id"""

    match_id: str = Field(
        description="The match_id of the selected match from the provided matches"
    )
    match_reason: str = Field(
        description="Reason for the match (e.g., 'exact abbreviation match', 'spousal reference', 'name variant')"
    )
    score: float = Field(description="Confidence score between 0 and 1")


class NameMatchSelectionResponse(BaseModel):
    """LLM response containing selected match IDs"""

    monologue: str = Field(description="A monologue to explain the match reason")
    selected_matches: list[MatchSelection] = Field(
        default_factory=list,
        description="list of selected match_ids with match_reason and score. Return only the best few matches (no more than 5), ordered by relevance."
    )


prompt = """
You are a scientific data matcher for biographical and taxonomic records.

When given a person's name query (e.g. "H. H. Smith") and a list of Bionomia API matches,
you must:
1. Analyze which matches are most relevant to the query
2. Select the match_ids of the most relevant matches
3. For each selected match, provide a match_reason and confidence score

CRITICAL: You MUST populate selected_matches with match_ids from the provided matches.
Do not leave selected_matches empty. Return the match_id (as a string) for each relevant match.

For each match in selected_matches:
- Use the exact match_id from the provided matches list
- Include a "match_reason" explaining why this match is relevant (e.g., "exact abbreviation match", "spousal reference", "name variant")
- Include a confidence "score" between 0 and 1 based on how well it matches the query
- Return only the best few matches (no more than 5), ordered by relevance (highest score first)
"""


async def find_best_name_match(
        name: str, bionomia_matches: list[BionomiaNameRecord | dict]
) -> NameMatchResult:
    # Convert all matches to BionomiaNameRecord objects and assign match_ids
    matches_with_ids = []
    match_id_to_match = {}

    for idx, match in enumerate(bionomia_matches):
        # Convert to BionomiaNameRecord if it's a dict
        if isinstance(match, dict):
            match_record = BionomiaNameRecord(**match)
        else:
            match_record = match

        # Use existing 'id' field if available, otherwise use index-based ID
        match_id = str(
            match_record.id if match_record.id is not None else f"match_{idx}"
        )

        # Create a dict copy with match_id for LLM
        match_dict = match_record.model_dump(exclude_none=True)
        match_dict["match_id"] = match_id
        matches_with_ids.append(match_dict)
        match_id_to_match[match_id] = match_record

    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"Bionomia API matches (each has a 'match_id' field): {json.dumps(matches_with_ids, indent=2)}",
        },
        {"role": "user", "content": f"Find the closest match for the name: {name}"},
    ]

    client = await get_client()
    selection_response = await client.chat.completions.create(
        messages=messages,
        response_model=NameMatchSelectionResponse,
        max_retries=3
    )

    # Validate IDs and add match_reason and score to original match objects
    top_matches = []
    for selection in selection_response.selected_matches:
        match_id = selection.match_id
        if match_id not in match_id_to_match:
            logger.warning(
                f"Invalid match_id '{match_id}' returned by LLM for name '{name}'. Skipping."
            )
            continue

        match_record = match_id_to_match[match_id]

        # Add match_reason and LLM confidence score to the record
        match_dict = match_record.model_dump(exclude_none=True)
        match_dict["match_reason"] = selection.match_reason
        match_dict["match_confidence"] = selection.score  # LLM confidence score

        top_matches.append(match_dict)

    # Sort by llm match_confidence (highest first)
    top_matches.sort(key=lambda x: x.get("match_confidence", 0), reverse=True)

    logger.info(
        f"Matched persons for '{name}': monologue='{selection_response.monologue}', matches={top_matches}"
    )

    result = {
        "monologue": selection_response.monologue,
        "matches": top_matches,
    }

    return result
