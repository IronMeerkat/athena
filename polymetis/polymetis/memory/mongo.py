from __future__ import annotations

import os
from typing import Optional

from pymongo import MongoClient
from bson.codec_options import CodecOptions

from polymetis.memory.bson_codecs import CODEC_OPTIONS


_mongo_client: Optional[MongoClient] = None
_mongo_uri_cached: Optional[str] = None


def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    """Return a MongoClient connected to the cluster.

    Reads MONGODB_URI from the environment by default. Caches a singleton per-URI.
    """
    global _mongo_client, _mongo_uri_cached
    eff_uri = uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    if _mongo_client is None or _mongo_uri_cached != eff_uri:
        _mongo_client = MongoClient(eff_uri)
        _mongo_uri_cached = eff_uri
    return _mongo_client


def get_sensitive_db(client: Optional[MongoClient] = None):
    """Return handle to the 'sensitive' database.

    Predefined collections are created by the container init script.
    """
    cli = client or get_mongo_client()
    # Apply JSON-friendly BSON decoding so query results are JSON-serializable
    return cli.get_database("sensitive", codec_options=CODEC_OPTIONS)


