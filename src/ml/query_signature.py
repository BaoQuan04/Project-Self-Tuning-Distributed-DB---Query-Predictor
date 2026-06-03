"""Helpers for exact query signatures used by cache-aware prediction."""
import json
from typing import Dict, Tuple


def canonical_params(params: dict = None) -> str:
    """Return stable JSON so the same logical query has one signature."""
    return json.dumps(params or {}, sort_keys=True, separators=(",", ":"))


def make_query_signature(query_type: str, table: str, params: dict = None) -> str:
    return f"{query_type}:{table}|{canonical_params(params)}"


def parse_query_signature(signature: str) -> Tuple[str, str, Dict]:
    """
    Parse signatures produced by make_query_signature.

    Backward compatible with older state strings like "SELECT:products".
    """
    if "|" in signature:
        state, raw_params = signature.split("|", 1)
        params = json.loads(raw_params) if raw_params else {}
    else:
        state, params = signature, {}

    query_type, table = state.split(":", 1)
    return query_type, table, params
