"""
QueryExecutor — executes queries in 3 modes:
  Mode 1 (no_cache):    direct DB hit every time
  Mode 2 (cache_only):  check cache → miss → hit DB → store in cache
  Mode 3 (ai_prefetch): same as cache_only but cache may already be warm from pre-fetch
"""
import time
from src.database.db_manager import DistributedDBManager
from src.database.cache_manager import CacheManager


class QueryExecutor:
    def __init__(self, db_manager: DistributedDBManager, cache_manager: CacheManager = None):
        self.db = db_manager
        self.cache = cache_manager

    def execute(self, table: str, query_type: str, params: dict = None, mode: str = "no_cache") -> dict:
        params = params or {}
        start = time.perf_counter()

        if mode == "no_cache":
            result = self._exec_no_cache(table, query_type, params)
        elif mode == "cache_only":
            result = self._exec_cache(table, query_type, params, is_prefetch_check=False)
        elif mode == "ai_prefetch":
            result = self._exec_cache(table, query_type, params, is_prefetch_check=True)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "table": table,
            "query_type": query_type,
            "params": params,
            "mode": mode,
            "response_time_ms": round(elapsed_ms, 3),
            "cache_hit": result["cache_hit"],
            "row_count": len(result["data"]),
        }

    def _exec_no_cache(self, table, query_type, params) -> dict:
        data = self.db.execute_query(table, query_type, params)
        return {"data": data, "cache_hit": False}

    def _exec_cache(self, table, query_type, params, is_prefetch_check) -> dict:
        if query_type == "SELECT" and self.cache:
            cached = self.cache.get(table, params, is_prefetch_check=is_prefetch_check)
            if cached is not None:
                return {"data": cached, "cache_hit": True}

        data = self.db.execute_query(table, query_type, params)

        if query_type == "SELECT" and self.cache:
            self.cache.set(table, params, data)

        return {"data": data, "cache_hit": False}
