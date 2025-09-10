from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

from bson import ObjectId, Decimal128
from bson.binary import Binary
from bson.codec_options import CodecOptions, TypeCodec, TypeRegistry


class _NeverType:
    """Sentinel type that is never used for encoding.

    Using this as python_type prevents altering built-in encoders
    while still allowing decoder behavior via bson_type.
    """
    pass


class ObjectIdAsStringCodec(TypeCodec):
    python_type = _NeverType  # type: ignore[assignment]
    bson_type = ObjectId  # type: ignore[assignment]

    def transform_python(self, value: _NeverType) -> _NeverType:  # no-op; never used
        return value

    def transform_bson(self, value: ObjectId) -> str:
        # Decode ObjectId to JSON-friendly string
        return str(value)


class DateTimeAsISOStringCodec(TypeCodec):
    python_type = _NeverType  # type: ignore[assignment]
    bson_type = datetime  # type: ignore[assignment]

    def transform_python(self, value: _NeverType) -> _NeverType:  # no-op; never used
        return value

    def transform_bson(self, value: datetime) -> str:
        # Convert to ISO 8601 string on decode for JSON friendliness
        return value.isoformat()


class Decimal128AsStringCodec(TypeCodec):
    python_type = _NeverType  # type: ignore[assignment]
    bson_type = Decimal128  # type: ignore[assignment]

    def transform_python(self, value: _NeverType) -> _NeverType:  # no-op; never used
        return value

    def transform_bson(self, value: Decimal128) -> str:
        # Represent as string to avoid precision loss in JSON
        return str(value)


class BinaryAsBase64StringCodec(TypeCodec):
    python_type = _NeverType  # type: ignore[assignment]
    bson_type = Binary  # type: ignore[assignment]

    def transform_python(self, value: _NeverType) -> _NeverType:  # no-op; never used
        return value

    def transform_bson(self, value: Binary) -> str:
        # Base64-encode bytes for JSON transport
        return base64.b64encode(bytes(value)).decode("ascii")


def build_json_friendly_codec_options() -> CodecOptions:
    """CodecOptions that decode common BSON types into JSON-friendly primitives.

    - ObjectId -> str
    - datetime -> ISO 8601 str
    - Decimal128 -> str
    - Binary -> base64 str
    """
    type_registry = TypeRegistry(
        [
            ObjectIdAsStringCodec(),
            DateTimeAsISOStringCodec(),
            Decimal128AsStringCodec(),
            BinaryAsBase64StringCodec(),
        ]
    )
    return CodecOptions(type_registry=type_registry)


# Default, ready-to-use options
CODEC_OPTIONS: CodecOptions = build_json_friendly_codec_options()


