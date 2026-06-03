"""
QueryLogger — maintains an in-memory sliding window of recent queries for ML input.
"""
from collections import deque, defaultdict
from datetime import datetime
from src.ml.query_signature import make_query_signature, canonical_params


class QueryLogger:
    def __init__(self, window_size: int = 20):
        self._history = deque(maxlen=window_size)

    def log(self, table: str, query_type: str, params: dict = None):
        params = params or {}
        self._history.append({
            "timestamp": datetime.now().isoformat(),
            "table": table,
            "query_type": query_type,
            "params": params,
            "state": f"{query_type}:{table}",
            "signature": make_query_signature(query_type, table, params),
        })

    def recent_states(self, n: int = 5) -> list:
        """Return last n (query_type, table) state strings."""
        items = list(self._history)
        return [item["state"] for item in items[-n:]]

    def recent_signatures(self, n: int = 5) -> list:
        """Return last n exact query signatures, including normalized params."""
        items = list(self._history)
        return [item["signature"] for item in items[-n:]]

    def recent_tables(self, n: int = 5) -> list:
        items = list(self._history)
        return [item["table"] for item in items[-n:]]

    def last_entry(self) -> dict:
        if self._history:
            return self._history[-1]
        return {}

    def recent_params_by_table(self, n: int = 5) -> dict:
        """Return {table: [last n canonical param strings]} for SELECT queries only."""
        result = defaultdict(list)
        for item in self._history:
            if item["query_type"] == "SELECT":
                result[item["table"]].append(canonical_params(item["params"]))
        return {table: params[-n:] for table, params in result.items()}

    def all(self) -> list:
        return list(self._history)
