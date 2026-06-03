"""
BenchmarkRunner — runs 3 scenarios on identical test query sequences and collects metrics.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import random
import json
import pandas as pd
from tqdm import tqdm

from config.settings import (
    BENCHMARK_QUERIES, LOGS_CSV, MODELS_DIR, REPORTS_DIR,
)
from src.database.db_manager import DistributedDBManager
from src.database.cache_manager import CacheManager
from src.query_engine.query_executor import QueryExecutor
from src.query_engine.query_logger import QueryLogger
from src.query_engine.prefetch_controller import PrefetchController
from src.ml.markov_predictor import MarkovPredictor
from src.ml.feature_extractor import extract_signature_sequences
from src.benchmark.metrics_collector import MetricsCollector

random.seed(123)


def load_test_queries(n: int = BENCHMARK_QUERIES, preserve_sessions: bool = True) -> list:
    """Load benchmark workload, preserving session order by default."""
    df = pd.read_csv(LOGS_CSV)

    if preserve_sessions:
        df["_ts"] = pd.to_datetime(df["timestamp"])
        session_order = df.groupby("session_id")["_ts"].min().sort_values().index
        chunks = []
        total = 0
        for session_id in session_order:
            grp = df[df["session_id"] == session_id].sort_values("_ts")
            chunks.append(grp)
            total += len(grp)
            if total >= n:
                break
        df = pd.concat(chunks, ignore_index=True).head(n)
    else:
        df = df.sample(n=min(n, len(df)), random_state=42).reset_index(drop=True)

    queries = []
    for _, row in df.iterrows():
        try:
            params = json.loads(row["query_params"])
        except Exception:
            params = {"limit": 20}
        queries.append({
            "session_id": row["session_id"],
            "table": row["table_name"],
            "query_type": row["query_type"],
            "params": params,
        })
    return queries


def run_scenario(scenario: str, queries: list, db: DistributedDBManager,
                 cache: CacheManager = None, predictor=None,
                 isolate_sessions: bool = True) -> MetricsCollector:
    collector = MetricsCollector(scenario)
    executor = QueryExecutor(db, cache)
    logger = QueryLogger(window_size=10)
    prefetch_ctrl = None

    if predictor and scenario == "ai_prefetch":
        prefetch_ctrl = PrefetchController(predictor, cache, db, async_mode=False)

    mode_map = {
        "baseline": "no_cache",
        "cache_only": "cache_only",
        "ai_prefetch": "ai_prefetch",
    }
    mode = mode_map[scenario]

    if cache:
        cache.flush()

    last_session_id = None
    for q in tqdm(queries, desc=f"  {scenario}", leave=False):
        if isolate_sessions and q.get("session_id") != last_session_id:
            if cache:
                cache.flush()
            logger = QueryLogger(window_size=10)
            last_session_id = q.get("session_id")

        result = executor.execute(q["table"], q["query_type"], q["params"], mode=mode)
        collector.record(result)
        logger.log(q["table"], q["query_type"], q["params"])

        if prefetch_ctrl:
            prefetch_ctrl.on_query_executed(
                logger.recent_signatures(5),
            )

    if cache:
        cache_stats = cache.stats
        collector.set_extra({
            "redis_hits": cache_stats["hits"],
            "redis_misses": cache_stats["misses"],
            "redis_prefetch_hits": cache_stats["prefetch_hits"],
        })
    if prefetch_ctrl:
        collector.set_extra(prefetch_ctrl.stats)

    return collector


def _load_or_train_signature_predictor() -> MarkovPredictor:
    """Prefer the exact-query Markov model because it predicts cache keys."""
    signature_path = os.path.join(MODELS_DIR, "markov_signature_model.pkl")
    if os.path.exists(signature_path):
        print("Using exact-query Markov predictor.")
        return MarkovPredictor.load(signature_path)

    if os.path.exists(LOGS_CSV):
        print("Exact-query model not found; training it from query logs.")
        df = pd.read_csv(LOGS_CSV)
        sequences = extract_signature_sequences(df)
        predictor = MarkovPredictor(order=2)
        predictor.train(sequences)
        os.makedirs(MODELS_DIR, exist_ok=True)
        predictor.save(signature_path)
        print(f"Saved exact-query predictor -> {signature_path}")
        return predictor

    raise FileNotFoundError("No query logs found. Run python main.py genlogs first.")


def run_all(n_queries: int = BENCHMARK_QUERIES) -> dict:
    print(f"\n{'='*60}")
    print(f"BENCHMARK: {n_queries:,} queries × 3 scenarios")
    print(f"{'='*60}")

    queries = load_test_queries(n_queries, preserve_sessions=True)
    print(f"Test queries loaded: {len(queries):,}")

    # Load predictor
    predictor = _load_or_train_signature_predictor()

    results = {}
    with DistributedDBManager() as db:
        cache = CacheManager()

        print("\n[1/3] Baseline (no cache, no prediction)...")
        results["baseline"] = run_scenario("baseline", queries, db).summary()

        print("[2/3] Cache Only...")
        results["cache_only"] = run_scenario("cache_only", queries, db, cache).summary()

        print("[3/3] AI Pre-fetch...")
        results["ai_prefetch"] = run_scenario("ai_prefetch", queries, db, cache, predictor).summary()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, "benchmark_summary.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved → {report_path}")

    _print_table(results)
    return results


def _print_table(results: dict):
    from tabulate import tabulate
    rows = []
    for scenario, s in results.items():
        rows.append([
            scenario,
            f"{s['cache_hit_rate_pct']}%",
            f"{s['avg_response_ms']} ms",
            f"{s['p95_response_ms']} ms",
            f"{s['p99_response_ms']} ms",
        ])
    headers = ["Scenario", "Cache Hit Rate", "Avg RT", "P95 RT", "P99 RT"]
    print("\n" + tabulate(rows, headers=headers, tablefmt="github"))


if __name__ == "__main__":
    run_all()
