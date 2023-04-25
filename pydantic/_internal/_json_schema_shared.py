"""
Types and utility functions used by various other internal tools.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Union

from pydantic_core import core_schema

JsonSchemaValue = Dict[str, Any]
CoreSchemaOrField = Union[core_schema.CoreSchema, core_schema.DataclassField, core_schema.TypedDictField]


class GetJsonSchemaHandler:
    def __call__(self, __core_schema: CoreSchemaOrField) -> JsonSchemaValue:
        raise NotImplementedError

    def resolve_ref_schema(self, __maybe_ref_json_schema: JsonSchemaValue) -> JsonSchemaValue:
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
