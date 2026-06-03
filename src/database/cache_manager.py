"""
CacheManager — Redis-backed cache with hit/miss tracking.
"""
import json
import hashlib
import decimal
import datetime
import redis
from config.settings import REDIS, CACHE_TTL, CACHE_KEY_PREFIX


class _Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        return super().default(obj)


class CacheManager:
    def __init__(self):
        self._client = redis.Redis(**REDIS, decode_responses=True)
        self._hits = 0
        self._misses = 0
        self._prefetch_hits = 0
        self._last_hit_source = None
        # cumulative across all flush() calls — never reset
        self._total_hits = 0
        self._total_misses = 0
        self._total_prefetch_hits = 0

    def _make_key(self, table: str, params: dict) -> str:
        raw = f"{table}:{json.dumps(params, sort_keys=True)}"
        digest = hashlib.md5(raw.encode()).hexdigest()[:12]
        return f"{CACHE_KEY_PREFIX}:{table}:{digest}"

    def get(self, table: str, params: dict, is_prefetch_check: bool = False):
        key = self._make_key(table, params)
        val = self._client.get(key)
        if val is not None:
            self._hits += 1
            self._total_hits += 1
            payload = json.loads(val)
            if isinstance(payload, dict) and "__qp_cache_meta__" in payload:
                source = payload["__qp_cache_meta__"].get("source")
                data = payload["data"]
            else:
                source = "unknown"
                data = payload
            self._last_hit_source = source
            if is_prefetch_check and source == "prefetch":
                self._prefetch_hits += 1
                self._total_prefetch_hits += 1
            return data
        self._misses += 1
        self._total_misses += 1
        self._last_hit_source = None
        return None

    def set(self, table: str, params: dict, data: list, ttl: int = None, source: str = "normal"):
        key = self._make_key(table, params)
        payload = {
            "__qp_cache_meta__": {"source": source},
            "data": data,
        }
        self._client.setex(key, ttl or CACHE_TTL, json.dumps(payload, cls=_Encoder))

    def invalidate(self, table: str, params: dict):
        key = self._make_key(table, params)
        self._client.delete(key)

    def flush(self):
        self._client.flushdb()
        self._hits = 0
        self._misses = 0
        self._prefetch_hits = 0

    @property
    def hit_rate(self) -> float:
        total = self._total_hits + self._total_misses
        return self._total_hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        total = self._total_hits + self._total_misses
        return {
            "hits": self._total_hits,
            "misses": self._total_misses,
            "total": total,
            "hit_rate": round(self.hit_rate * 100, 2),
            "prefetch_hits": self._total_prefetch_hits,
        }

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False
