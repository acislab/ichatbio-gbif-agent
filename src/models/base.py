from __future__ import annotations
from pydantic import (
    BaseModel,
    ConfigDict,
)


class ProductionBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",  # Forbid extra fields not in the model
        validate_assignment=True,  # Validate when values are assigned
        from_attributes=True,  # Allow loading from objects with attributes
        populate_by_name=True,  # Allow population by field name OR alias
        validate_default=True,  # Validate default values
    )
