from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Literal
from bson import ObjectId, Decimal128
from bson.binary import Binary
from datetime import datetime
import base64

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo import MongoClient

from polymetis.tools.registry import (
    SENSITIVE_TOOLS as TOOL_REGISTRY,
    ToolSpec,
)
from polymetis.memory.mongo import get_mongo_client, get_sensitive_db
from polymetis.agents.utils import _json_safe

from athena_logging import get_logger

logger = get_logger(__name__)

PREDEFINED_COLLECTIONS: set[str] = {"User", "Location", "Schedule"}



class MongoOpArgs(TypedDict, total=False):
    op: Literal[
        "create_collection",
        "drop_collection",
        "list_collections",
        "insert_one",
        "insert_many",
        "find_one",
        "find",
        "update_one",
        "update_many",
        "delete_one",
        "delete_many",
        "aggregate",
        "count_documents",
        "distinct",
        "create_index",
        "drop_index",
    ]
    collection: str
    document: Dict[str, Any]
    documents: List[Dict[str, Any]]
    filter: Dict[str, Any]
    update: Dict[str, Any]
    pipeline: List[Dict[str, Any]]
    index: Dict[str, Any]
    index_name: str
    options: Dict[str, Any]
    limit: int
    skip: int
    sort: List[List[Any]]


def _get_collection(db: Database, name: str) -> Collection:
    return db.get_collection(name)


def _assert_collection_mutation_allowed(name: str, op: str) -> None:
    if name in PREDEFINED_COLLECTIONS and op in {"drop_collection", "create_collection"}:
        raise PermissionError(
            f"Operation '{op}' is not allowed on predefined collection '{name}'"
        )




def _call_mongo(args: MongoOpArgs) -> Any:
    client: MongoClient = get_mongo_client()
    db: Database = get_sensitive_db(client)
    op = args["op"]

    # Collection-level ops
    if op == "list_collections":
        return [c["name"] for c in db.list_collections()]

    if op == "create_collection":
        name = str(args["collection"])
        _assert_collection_mutation_allowed(name, op)
        options = args.get("options") or {}
        db.create_collection(name, **options)
        return {"ok": True}

    if op == "drop_collection":
        name = str(args["collection"])
        _assert_collection_mutation_allowed(name, op)
        db.drop_collection(name)
        return {"ok": True}

    # Document-level ops
    collection = str(args["collection"])
    coll = _get_collection(db, collection)

    if op == "insert_one":
        doc = args.get("document") or {}
        res = coll.insert_one(doc)
        return {"inserted_id": str(res.inserted_id)}

    if op == "insert_many":
        docs = args.get("documents") or []
        res = coll.insert_many(docs)
        return {"inserted_ids": [str(_id) for _id in res.inserted_ids]}

    if op == "find_one":
        flt = args.get("filter") or {}
        doc = coll.find_one(flt)
        return _json_safe(doc) if doc is not None else None

    if op == "find":
        flt = args.get("filter") or {}
        limit = int(args.get("limit", 0) or 0)
        skip = int(args.get("skip", 0) or 0)
        sort = args.get("sort") or []
        cursor = coll.find(flt)
        if sort:
            cursor = cursor.sort(sort)  # type: ignore[arg-type]
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        out: list[dict[str, Any]] = []
        for d in cursor:
            out.append(_json_safe(d))
        return out

    if op == "update_one":
        flt = args.get("filter") or {}
        upd = args.get("update") or {}
        res = coll.update_one(flt, upd)
        return {"matched": res.matched_count, "modified": res.modified_count}

    if op == "update_many":
        flt = args.get("filter") or {}
        upd = args.get("update") or {}
        res = coll.update_many(flt, upd)
        return {"matched": res.matched_count, "modified": res.modified_count}

    if op == "delete_one":
        flt = args.get("filter") or {}
        res = coll.delete_one(flt)
        return {"deleted": res.deleted_count}

    if op == "delete_many":
        flt = args.get("filter") or {}
        res = coll.delete_many(flt)
        return {"deleted": res.deleted_count}

    if op == "aggregate":
        pipeline = args.get("pipeline") or []
        out: list[dict[str, Any]] = []
        for d in coll.aggregate(pipeline):
            out.append(_json_safe(d))
        return out

    if op == "count_documents":
        flt = args.get("filter") or {}
        return int(coll.count_documents(flt))

    if op == "distinct":
        key = str(args["index_name"])
        return list(coll.distinct(key, args.get("filter") or {}))

    if op == "create_index":
        index = args["index"]
        name = coll.create_index(list(index.items()))
        return {"index_name": name}

    if op == "drop_index":
        idx_name = str(args["index_name"])
        coll.drop_index(idx_name)
        return {"ok": True}

    raise ValueError(f"Unsupported op: {op}")


TOOL_REGISTRY.register(
    ToolSpec(
        name="mongo.admin",
        description=(
            "Admin-level Mongo access on 'sensitive' DB. Full CRUD and admin ops on arbitrary collections, "
            "except schema changes or drop on predefined collections (User, Location, Schedule)."
        ),
        schema={
            "type": "object",
            "properties": {
                "op": {
                    "type": "string",
                    "enum": [
                        "create_collection",
                        "drop_collection",
                        "list_collections",
                        "insert_one",
                        "insert_many",
                        "find_one",
                        "find",
                        "update_one",
                        "update_many",
                        "delete_one",
                        "delete_many",
                        "aggregate",
                        "count_documents",
                        "distinct",
                        "create_index",
                        "drop_index",
                    ],
                },
                "collection": {"type": "string"},
                "document": {"type": "object"},
                "documents": {"type": "array", "items": {"type": "object"}},
                "filter": {"type": "object"},
                "update": {"type": "object"},
                # Aggregate pipeline is an array of stage objects
                "pipeline": {"type": "array", "items": {"type": "object"}},
                "index": {"type": "object"},
                "index_name": {"type": "string"},
                "options": {"type": "object"},
                "limit": {"type": "integer"},
                "skip": {"type": "integer"},
                # Sort is an array of [field, direction] pairs
                "sort": {"type": "array", "items": {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]}}},
            },
            "required": ["op"],
        },
    ),
    _call_mongo,
)


