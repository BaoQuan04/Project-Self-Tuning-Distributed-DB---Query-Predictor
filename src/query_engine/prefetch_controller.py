"""
PrefetchController — after each query, predicts the next and pre-fetches its data
into Redis cache asynchronously (background thread), so the next query is a cache hit.
"""
import threading
from src.database.db_manager import DistributedDBManager
from src.database.cache_manager import CacheManager
from config.settings import PREDICTION_CONFIDENCE_THRESHOLD
from src.ml.query_signature import parse_query_signature


class PrefetchController:
    def __init__(self, predictor, cache_manager: CacheManager, db_manager: DistributedDBManager,
                 confidence_threshold: float = PREDICTION_CONFIDENCE_THRESHOLD,
                 async_mode: bool = True):
        self.predictor = predictor
        self.cache = cache_manager
        self.db = db_manager
        self.threshold = confidence_threshold
        self.async_mode = async_mode
        self._prefetch_attempts = 0
        self._prefetch_successes = 0
        self._prediction_count = 0
        self._skipped_low_confidence = 0
        self._skipped_non_select = 0

    def on_query_executed(self, recent_states: list, default_params: dict = None):
        """Call this after each query. Spawns background pre-fetch if confident."""
        if not recent_states:
            return

        try:
            prediction, confidence = self.predictor.predict_next(recent_states)
        except Exception:
            return

        self._prediction_count += 1
        if confidence < self.threshold:
            self._skipped_low_confidence += 1
            return

        query_type, table, predicted_params = parse_query_signature(prediction)
        if query_type != "SELECT":
            self._skipped_non_select += 1
            return

        params = predicted_params or default_params or {"limit": 20}
        if self.async_mode:
            thread = threading.Thread(target=self._prefetch, args=(table, params), daemon=True)
            thread.start()
        else:
            self._prefetch(table, params)

    def _prefetch(self, table: str, params: dict):
        self._prefetch_attempts += 1
        try:
            data = self.db.fetch_from_remote(table, params)
            self.cache.set(table, params, data, source="prefetch")
            self._prefetch_successes += 1
        except Exception:
            pass

    @property
    def stats(self) -> dict:
        return {
            "prefetch_attempts": self._prefetch_attempts,
            "prefetch_successes": self._prefetch_successes,
            "prediction_count": self._prediction_count,
            "skipped_low_confidence": self._skipped_low_confidence,
            "skipped_non_select": self._skipped_non_select,
        }
