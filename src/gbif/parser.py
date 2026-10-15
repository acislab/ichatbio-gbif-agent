import datetime
import json
from importlib import resources
from typing import Type, Optional, TypeVar

from instructor.core.exceptions import InstructorRetryException
from pydantic import BaseModel, Field, create_model
from tenacity import retry, stop_after_attempt, wait_exponential

from src.instructor_client import get_client
from src.models.location import ResolvedLocation, GadmMatchType
from src.utils import UserRequestExpansion, IdentifiedOrganism

CURRENT_DATE = datetime.datetime.now().strftime("%B %d, %Y")


def create_response_model(parameter_model: Type[BaseModel]) -> Type[BaseModel]:
    DynamicModel = create_model(
        "LLMResponse",
        plan=(
            str,
            Field(
                description="A brief explanation of what API parameters you plan to use. Or, if you are unable to fulfill the user's request using the available API parameters, provide a brief explanation for why you cannot retrieve the requested records. You can use the closest matching parameters available in the api parameter_model (params) to the user's request and explain why you used them."
            ),
        ),
        params=(
            Optional[parameter_model],
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
    response_model = create_response_model(parameters_model)

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
        # TODO: don't silence exceptions!
        # Access failed attempts for debugging
        print(f"Failed after {e.n_attempts} attempts")
        print(f"Exception details: {e}")
    except Exception as e:
        # TODO: don't silence exceptions!
        print(f"Exception details: {e}")

    return response
