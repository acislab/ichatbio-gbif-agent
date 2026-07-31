import asyncio
import datetime
import enum
import json
import keyword
import re
from importlib import resources
from typing import Type, Optional, TypeVar

from instructor.core.exceptions import InstructorRetryException
from pydantic import BaseModel, Field, create_model
from tenacity import retry, stop_after_attempt, wait_exponential

from src.instructor_client import get_client
from src.gbif.param_normalizer import _fetch_vocabulary_concepts
from src.models.location import ResolvedLocation, GadmMatchType
from src.models.occurrences import InvasiveSpeciesFilters
from src.log import logger
from src.utils import UserRequestExpansion, IdentifiedOrganism

CURRENT_DATE = datetime.datetime.now().strftime("%B %d, %Y")

VOCABULARY_FIELD_TO_NAME = {
    "degreeOfEstablishment": "DegreeOfEstablishment",
    "establishmentMeans": "EstablishmentMeans",
    "pathway": "Pathway",
}


def _sanitize_enum_member_name(value: str, used_names: set[str]) -> str:
    sanitized = re.sub(r"\W+", "_", value).strip("_")
    if not sanitized:
        sanitized = "VALUE"
    if sanitized[0].isdigit() or keyword.iskeyword(sanitized.lower()):
        sanitized = f"VALUE_{sanitized}"
    sanitized = sanitized.upper()

    candidate = sanitized
    suffix = 2
    while candidate in used_names:
        candidate = f"{sanitized}_{suffix}"
        suffix += 1

    used_names.add(candidate)
    return candidate


def _coerce_schema_example_value(value):
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _reconcile_field_examples(examples, allowed_values: set[str]):
    if not examples:
        return None

    reconciled_examples = []
    for example in examples:
        if isinstance(example, (list, tuple)):
            reconciled = []
            for item in example:
                item_value = _coerce_schema_example_value(item)
                if isinstance(item_value, str) and item_value in allowed_values:
                    reconciled.append(item_value)
                else:
                    reconciled = []
                    break
            if reconciled:
                reconciled_examples.append(reconciled)
            continue

        example_value = _coerce_schema_example_value(example)
        if isinstance(example_value, str) and example_value in allowed_values:
            reconciled_examples.append(example_value)

    return reconciled_examples or None

# Build a vocabulary enum from a list of fetched concepts & drops deprecated ones.
def _build_vocabulary_enum_from_concepts(
    vocabulary_name: str, concepts: list[dict]
) -> type[enum.Enum]:
    canonical_values = sorted(
        {
            concept["name"]
            for concept in concepts
            if isinstance(concept, dict)
            and not concept.get("deprecated")
            and isinstance(concept.get("name"), str)
            and concept.get("name")
        }
    )

    if not canonical_values:
        raise ValueError(
            f"No canonical (non-deprecated) concepts returned for vocabulary "
            f"'{vocabulary_name}'; refusing to build an empty enum."
        )

    used_names: set[str] = set()
    members = {
        _sanitize_enum_member_name(value, used_names): value
        for value in canonical_values
    }
    # construct the in-memory enum.Enum.
    return enum.Enum(vocabulary_name, members, type=str, module=__name__)


async def build_vocabulary_enum(vocabulary_name: str) -> type[enum.Enum]:
    # Fetch the vocabulary concepts from GBIF and build an enum.Enum class for the vocabulary
    concepts = await _fetch_vocabulary_concepts(vocabulary_name)
    return _build_vocabulary_enum_from_concepts(vocabulary_name, concepts)

# Build a dynamic InvasiveSpeciesFilters model with live vocabulary constraints.
# fetches all three vocabularies concurrently and rebuilds the InvasiveSpeciesFilters model with create_model  
async def _build_dynamic_invasive_species_filters() -> type[InvasiveSpeciesFilters]:
    vocabulary_names = list(VOCABULARY_FIELD_TO_NAME.values())
    fetched_vocabularies = await asyncio.gather(
        *(build_vocabulary_enum(vocabulary_name) for vocabulary_name in vocabulary_names),
        return_exceptions=True,
    )

    errors = {
        vocabulary_name: result
        for vocabulary_name, result in zip(vocabulary_names, fetched_vocabularies)
        if isinstance(result, Exception)
    }
    if errors:
        for vocabulary_name, error in errors.items():
            logger.warning(
                "Skipping live GBIF vocabulary constraint for %s; using unconstrained InvasiveSpeciesFilters: %s",
                vocabulary_name,
                error,
            )
        return InvasiveSpeciesFilters

    vocabulary_enums = dict(zip(vocabulary_names, fetched_vocabularies))
    field_definitions = {}
    for field_name, vocabulary_name in VOCABULARY_FIELD_TO_NAME.items():
        field_info = InvasiveSpeciesFilters.model_fields[field_name]
        enum_type = vocabulary_enums[vocabulary_name]
        allowed_values = {member.value for member in enum_type}
        field_definitions[field_name] = (
            Optional[list[enum_type]],
            Field(
                default=None,
                description=field_info.description,
                examples=_reconcile_field_examples(field_info.examples, allowed_values),
            ),
        )

    return create_model(
        "DynamicInvasiveSpeciesFilters",
        __base__=InvasiveSpeciesFilters,
        **field_definitions,
    )

# Build a response parameters model that incorporates live vocabulary constraints.
async def _build_response_parameters_model(
    parameter_model: Type[BaseModel],
) -> Type[BaseModel]:
    invasive_field_names = set(VOCABULARY_FIELD_TO_NAME)
    if not invasive_field_names.intersection(parameter_model.model_fields):
        return parameter_model

    dynamic_invasive_species_filters = await _build_dynamic_invasive_species_filters()
    if dynamic_invasive_species_filters is InvasiveSpeciesFilters:
        return parameter_model

    field_definitions = {}
    for field_name, vocabulary_name in VOCABULARY_FIELD_TO_NAME.items():
        if field_name not in parameter_model.model_fields:
            continue

        field_info = dynamic_invasive_species_filters.model_fields[field_name]
        field_definitions[field_name] = (
            field_info.annotation,
            Field(
                default=None,
                description=field_info.description,
                examples=field_info.examples,
            ),
        )

    if not field_definitions:
        return parameter_model

    return create_model(
        f"{parameter_model.__name__}WithLiveVocabularies",
        __base__=parameter_model,
        **field_definitions,
    )

# wraps all into the final LLMResponse schema, and parse() hands that schema to the LLM
async def create_response_model(parameter_model: Type[BaseModel]) -> Type[BaseModel]:
    response_parameter_model = await _build_response_parameters_model(parameter_model)

    DynamicModel = create_model(
        "LLMResponse",
        plan=(
            str,
            Field(
                description="A brief explanation of what API parameters you plan to use. Or, if you are unable to fulfill the user's request using the available API parameters, provide a brief explanation for why you cannot retrieve the requested records. You can use the closest matching parameters available in the api parameter_model (params) to the user's request and explain why you used them."
            ),
        ),
        params=(
            Optional[response_parameter_model],
            Field(
                description="API parameters values supplied from provided in the user request",
                default=None,
            ),
        ),
        unresolved_params=(
            Optional[list[str]],
            Field(
                description="The fields that need clarification to continue with the request.",
                default=None,
            ),
        ),
        artifact_description=(
            Optional[str],
            Field(
                description="A concise characterization of the retrieved records.",
                examples=[
                    "Per-country record counts for species Rattus rattus",
                ],
                default=None,
            ),
        ),
        clarification_needed=(
            Optional[bool],
            Field(
                description="If you are unable to determine the parameter for the value provided in the user request, set this to True",
                default=None,
            ),
        ),
        clarification_reason=(
            Optional[str],
            Field(
                description="The reason or a short note why the user request needs clarification about the parameter values",
                default=None,
            ),
        ),
        __base__=BaseModel,
    )

    class LLMResponseWithValidation(DynamicModel):
        def model_post_init(self, __context):
            if not self.clarification_needed and self.artifact_description is None:
                raise ValueError(
                    "artifact_description must not be None if clarification_needed is False."
                )

    return LLMResponseWithValidation


def get_system_prompt(entrypoint_id: str):
    prompt = resources.read_text("src.resources.prompts", "parse_api_parameters.md")

    entrypoint_examples = json.loads(resources.read_text("src.resources", "fewshot.json"))
    assert isinstance(entrypoint_examples, dict)

    examples = entrypoint_examples.get(entrypoint_id, ())
    for idx, example in enumerate(examples):
        example_text = f"""
### Example {idx + 1}:
```json
{json.dumps(example)}
```
"""
        prompt += example_text

    return prompt


def format_organisms_parsing_response(
        organisms: list[IdentifiedOrganism],
):
    message = f"""
    ```json
    Organisms identified in the user request: {
    json.dumps([
        organism.model_dump(exclude_none=True, mode="json")
        for organism in organisms
    ], indent=2)
    }
    ```
    """
    return message


def format_locations_parsing_response(
        locations: list[ResolvedLocation],
):
    display_locations = []
    overall_statuses = []

    for location in locations:
        loc_dict = location.model_dump(exclude_none=True, mode="json")
        match_type = loc_dict.get("match_type")
        loc_dict.pop("query_trace", None)
        if match_type == GadmMatchType.COMPLETE:
            status_msg = "successfully resolved to gadm"
        elif match_type == GadmMatchType.PARTIAL:
            status_msg = "partially resolved to gadm"
        else:
            status_msg = "not resolved to gadm"
        loc_dict["resolution_status"] = status_msg
        overall_statuses.append(status_msg)
        display_locations.append(loc_dict)

    message = f"""
    ```json
    Locations identified in the user request: {
    json.dumps(display_locations, indent=2)
    }
    ```
    """
    return message

T = TypeVar('T', bound=BaseModel)

# For validation errors - shorter delays
@retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3))
async def parse(
        request: str,
        entrypoint_id: str,
        parameters_model: Type[T],
        preprocess_information: Optional[UserRequestExpansion] = None,
) -> T:
    response_model = await create_response_model(parameters_model)

    client = await get_client()

    messages = [
        {
            "role": "system",
            "content": get_system_prompt(entrypoint_id),
        }
    ]
    if preprocess_information:
        if preprocess_information.reasoning:
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Preprocessed user request: Reasoning: {preprocess_information.reasoning}",
                }
            )
        if preprocess_information.organisms:
            messages.append(
                {
                    "role": "assistant",
                    "content": format_organisms_parsing_response(
                        preprocess_information.organisms
                    ),
                }
            )
        if preprocess_information.locations:
            messages.append(
                {
                    "role": "assistant",
                    "content": format_locations_parsing_response(
                        preprocess_information.locations
                    ),
                }
            )
    messages.append(
        {
            "role": "user",
            "content": f"Today's date is {CURRENT_DATE}. Generate GBIF Request Parameters for the following user request: {request}",
        }
    )

    instructor_validation_context = {"user_request": request}

    try:
        response = await client.chat.completions.create(
            messages=messages,
            response_model=response_model,
            context=instructor_validation_context,
            max_retries=3,
        )
    except InstructorRetryException as e:
        logger.error("LLM parse failed after %s attempts: %s", e.n_attempts, e)
        raise
    except Exception as e:
        logger.error("Unexpected error during LLM parse: %s", e)
        raise

    return response