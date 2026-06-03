import os

SITE_A = {
    "host": os.getenv("SITE_A_HOST", "localhost"),
    "port": int(os.getenv("SITE_A_PORT", 5435)),
    "database": os.getenv("SITE_A_DB", "site_a"),
    "user": os.getenv("SITE_A_USER", "postgres"),
    "password": os.getenv("SITE_A_PASSWORD", "123456"),
}

SITE_B = {
    "host": os.getenv("SITE_B_HOST", "localhost"),
    "port": int(os.getenv("SITE_B_PORT", 5433)),
    "database": os.getenv("SITE_B_DB", "site_b"),
    "user": os.getenv("SITE_B_USER", "postgres"),
    "password": os.getenv("SITE_B_PASSWORD", "123456"),
}

REDIS = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": 0,
}

TABLE_SITE_MAP = {
    "customers": "site_a",
    "orders": "site_a",
    "products": "site_b",
    "inventory": "site_b",
}

CACHE_TTL = 300
CACHE_KEY_PREFIX = "qp"

# simulated network latency (ms)
SITE_A_LATENCY_MS = 5
SITE_B_LATENCY_MS = 150

MARKOV_ORDER = 2
PREDICTION_CONFIDENCE_THRESHOLD = 0.6

BENCHMARK_QUERIES = 10_000
TEST_SPLIT_RATIO = 0.2

QUERY_LOG_SIZE = 500_000
NUM_CUSTOMERS = 10_000
NUM_PRODUCTS = 5_000
NUM_ORDERS = 50_000
NUM_INVENTORY_ITEMS = 5_000

DATA_DIR = "data"
RESULTS_DIR = "results"
CHARTS_DIR = "results/charts"
REPORTS_DIR = "results/reports"
MODELS_DIR = "models"
LOGS_CSV = "data/query_history_logs.csv"
