"""
MetricsCollector — aggregates query execution results into performance statistics.
"""
import numpy as np
from typing import List


class MetricsCollector:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self._results: List[dict] = []
        self._extra = {}

    def record(self, result: dict):
        self._results.append(result)

    def set_extra(self, extra: dict):
        self._extra.update(extra)

    def summary(self) -> dict:
        if not self._results:
            return {}

        times = np.array([r["response_time_ms"] for r in self._results])
        hits = sum(1 for r in self._results if r.get("cache_hit"))
        total = len(self._results)
        select_results = [r for r in self._results if r.get("query_type") == "SELECT"]
        select_total = len(select_results)
        select_hits = sum(1 for r in select_results if r.get("cache_hit"))

        summary = {
            "scenario": self.scenario,
            "total_queries": total,
            "cache_hits": hits,
            "cache_misses": total - hits,
            "cache_hit_rate_pct": round(hits / total * 100, 2),
            "select_queries": select_total,
            "select_cache_hits": select_hits,
            "select_cache_hit_rate_pct": round(select_hits / select_total * 100, 2) if select_total else 0.0,
            "avg_response_ms": round(float(np.mean(times)), 3),
            "median_response_ms": round(float(np.median(times)), 3),
            "p95_response_ms": round(float(np.percentile(times, 95)), 3),
            "p99_response_ms": round(float(np.percentile(times, 99)), 3),
            "min_response_ms": round(float(np.min(times)), 3),
            "max_response_ms": round(float(np.max(times)), 3),
            "std_response_ms": round(float(np.std(times)), 3),
        }
        summary.update(self._extra)
        return summary

    def raw_times(self) -> List[float]:
        return [r["response_time_ms"] for r in self._results]

    def raw_results(self) -> List[dict]:
        return list(self._results)
