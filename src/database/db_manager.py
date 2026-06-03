"""
DistributedDBManager — routes queries to Site A or Site B and simulates cross-site latency.
"""
import time
import random
import psycopg2
import psycopg2.extras
from config.settings import SITE_A, SITE_B, TABLE_SITE_MAP, SITE_A_LATENCY_MS, SITE_B_LATENCY_MS


class DistributedDBManager:
    def __init__(self):
        self._conns = {}

    def _get_conn(self, site: str):
        if site not in self._conns or self._conns[site].closed:
            cfg = SITE_A if site == "site_a" else SITE_B
            self._conns[site] = psycopg2.connect(**cfg)
            self._conns[site].autocommit = True
        return self._conns[site]

    def _simulate_latency(self, site: str):
        base_ms = SITE_A_LATENCY_MS if site == "site_a" else SITE_B_LATENCY_MS
        jitter = random.uniform(-base_ms * 0.2, base_ms * 0.2)
        time.sleep((base_ms + jitter) / 1000.0)

    def execute_query(self, table: str, query_type: str, params: dict = None) -> list:
        site = TABLE_SITE_MAP.get(table, "site_a")
        self._simulate_latency(site)
        conn = self._get_conn(site)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        sql, values = self._build_sql(table, query_type, params or {})
        cur.execute(sql, values)

        if query_type == "SELECT":
            rows = cur.fetchall()
            cur.close()
            return [dict(r) for r in rows]

        cur.close()
        return []

    def fetch_from_remote(self, table: str, params: dict = None) -> list:
        """Used by PrefetchController to pull data into cache."""
        return self.execute_query(table, "SELECT", params or {})

    def _build_sql(self, table: str, query_type: str, params: dict):
        if query_type == "SELECT":
            conditions = []
            values = []
            allowed_filters = {
                "customers": ["city", "country"],
                "orders": ["status", "customer_id"],
                "products": ["category", "brand"],
                "inventory": ["warehouse_id", "product_id"],
            }
            for col in allowed_filters.get(table, []):
                if col in params:
                    conditions.append(f"{col} = %s")
                    values.append(params[col])
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            limit = int(params.get("limit", 20))
            return f"SELECT * FROM {table} {where} LIMIT %s", values + [limit]

        elif query_type == "INSERT":
            if table == "orders":
                return (
                    "INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_price) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    [params.get("customer_id", 1), params.get("product_id", 1),
                     params.get("quantity", 1), params.get("unit_price", 100.0),
                     params.get("total_price", 100.0)],
                )
            elif table == "inventory":
                return (
                    "UPDATE inventory SET quantity = quantity + %s, last_updated = NOW() WHERE product_id = %s",
                    [params.get("quantity", 10), params.get("product_id", 1)],
                )

        elif query_type == "UPDATE":
            if table == "orders":
                return (
                    "UPDATE orders SET status = %s, updated_at = NOW() WHERE order_id = %s",
                    [params.get("status", "confirmed"), params.get("order_id", 1)],
                )
            elif table == "inventory":
                delta = params.get("delta", 0)
                return (
                    "UPDATE inventory SET quantity = GREATEST(0, quantity + %s), last_updated = NOW() WHERE product_id = %s",
                    [delta, params.get("product_id", 1)],
                )
            elif table == "customers":
                return (
                    "UPDATE customers SET updated_at = NOW() WHERE customer_id = %s",
                    [params.get("customer_id", 1)],
                )

        # fallback SELECT
        return f"SELECT * FROM {table} LIMIT 10", []

    def close(self):
        for conn in self._conns.values():
            if not conn.closed:
                conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
