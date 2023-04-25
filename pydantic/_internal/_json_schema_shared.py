"""
Types and utility functions used by various other internal tools.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Union

from pydantic_core import core_schema

JsonSchemaValue = Dict[str, Any]
CoreSchemaOrField = Union[core_schema.CoreSchema, core_schema.DataclassField, core_schema.TypedDictField]


class GetJsonSchemaHandler:
    """
    Handler to call into the next JSON schema generation function
    """

    def __call__(self, __core_schema: CoreSchemaOrField) -> JsonSchemaValue:
        """Call the inner handler and get the JsonSchemaValue it returns.
        This will call the next JSON schema modifying function up until it calls
        into `pydantic.json_schema.GenerateJsonSchema`, which will raise a
        `pydantic.errors.PydanticInvalidForJsonSchema` error if it cannot generate
        a JSON schema.

        Args:
            __core_schema (CoreSchemaOrField): A `pydantic_core.core_schema.CoreSchema`.

        Raises:
            NotImplementedError: _description_

        Returns:
            JsonSchemaValue: _description_
        """
        raise NotImplementedError

    def resolve_ref_schema(self, __maybe_ref_json_schema: JsonSchemaValue) -> JsonSchemaValue:
        """Get the real schema for a `{"$ref": ...}` schema.
        If the schema given is not a `$ref` schema, it will be returned as is.
        This means you don't have to check before calling this function.

        Args:
            __maybe_ref_json_schema (JsonSchemaValue): A JsonSchemaValue, ref based or not.

        Raises:
            LookupError: if the ref is not found.

        Returns:
            JsonSchemaValue: A JsonSchemaValue that has no `$ref`.
        """
        raise NotImplementedError


GetJsonSchemaFunction = Callable[[CoreSchemaOrField, GetJsonSchemaHandler], JsonSchemaValue]


class UnpackedRefJsonSchemaHandler(GetJsonSchemaHandler):
    original_schema: JsonSchemaValue | None = None

    def __init__(self, handler: GetJsonSchemaHandler) -> None:
        self.handler = handler

    def resolve_ref_schema(self, __maybe_ref_json_schema: JsonSchemaValue) -> JsonSchemaValue:
        return self.handler.resolve_ref_schema(__maybe_ref_json_schema)

    def __call__(self, __core_schema: CoreSchemaOrField) -> JsonSchemaValue:
        self.original_schema = self.handler(__core_schema)
        return self.resolve_ref_schema(self.original_schema)

    def update_schema(self, schema: JsonSchemaValue) -> JsonSchemaValue:
        if self.original_schema is None:
            # handler / our __call__ was never called
            return schema
        original_schema = self.resolve_ref_schema(self.original_schema)
        if original_schema is not self.original_schema and schema is not original_schema:
            # a new schema was returned
            original_schema.clear()
            original_schema.update(schema)
        # return self.original_schema, which may be a ref schema
        return self.original_schema


def wrap_json_schema_fn_for_model_or_custom_type_with_ref_unpacking(
    fn: GetJsonSchemaFunction,
) -> GetJsonSchemaFunction:
    def wrapped(schema_or_field: CoreSchemaOrField, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        wrapped_handler = UnpackedRefJsonSchemaHandler(handler)
        json_schema = fn(schema_or_field, wrapped_handler)
        json_schema = wrapped_handler.update_schema(json_schema)
        return json_schema

    return wrapped
