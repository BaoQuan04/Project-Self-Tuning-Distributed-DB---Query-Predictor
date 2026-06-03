"""
Generate Query_History_Logs dataset with realistic sequential, temporal, and session patterns.
Output: data/query_history_logs.csv (~500K rows)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import uuid
import csv
from datetime import datetime, timedelta
from tqdm import tqdm
from config.settings import QUERY_LOG_SIZE, LOGS_CSV, TABLE_SITE_MAP

random.seed(42)

TABLES = ["customers", "orders", "products", "inventory"]
QUERY_TYPES = ["SELECT", "INSERT", "UPDATE", "DELETE"]

# Realistic sequential patterns (weighted chains)
# Each entry: list of (query_type, table) tuples that tend to follow each other
SESSION_PATTERNS = {
    "browse": [
        ("SELECT", "products"),
        ("SELECT", "inventory"),
        ("SELECT", "products"),
        ("SELECT", "customers"),
        ("SELECT", "orders"),
    ],
    "purchase": [
        ("SELECT", "products"),
        ("SELECT", "inventory"),
        ("SELECT", "customers"),
        ("INSERT", "orders"),
        ("UPDATE", "inventory"),
    ],
    "admin_report": [
        ("SELECT", "orders"),
        ("SELECT", "customers"),
        ("SELECT", "products"),
        ("SELECT", "inventory"),
        ("UPDATE", "customers"),
    ],
    "inventory_mgmt": [
        ("SELECT", "inventory"),
        ("SELECT", "products"),
        ("UPDATE", "inventory"),
        ("INSERT", "inventory"),
        ("SELECT", "products"),
    ],
    "customer_service": [
        ("SELECT", "customers"),
        ("SELECT", "orders"),
        ("UPDATE", "orders"),
        ("SELECT", "products"),
        ("SELECT", "customers"),
    ],
    "analytics": [
        ("SELECT", "orders"),
        ("SELECT", "customers"),
        ("SELECT", "products"),
        ("SELECT", "orders"),
        ("SELECT", "inventory"),
    ],
}

PATTERN_WEIGHTS = {
    "browse": 0.30,
    "purchase": 0.25,
    "admin_report": 0.15,
    "inventory_mgmt": 0.12,
    "customer_service": 0.10,
    "analytics": 0.08,
}

# Peak hours have higher activity
def sample_timestamp(base_date: datetime) -> datetime:
    hour_weights = {
        0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 2,
        6: 5, 7: 8, 8: 12, 9: 20, 10: 22, 11: 18,
        12: 10, 13: 12, 14: 22, 15: 20, 16: 15, 17: 12,
        18: 10, 19: 15, 20: 12, 21: 8, 22: 5, 23: 3,
    }
    hours = list(hour_weights.keys())
    weights = list(hour_weights.values())
    hour = random.choices(hours, weights=weights)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    day_offset = random.randint(0, 89)  # 3 months of history
    ts = base_date - timedelta(days=day_offset)
    ts = ts.replace(hour=hour, minute=minute, second=second)
    # Weekends have 40% of weekday traffic
    if ts.weekday() >= 5 and random.random() < 0.6:
        ts += timedelta(days=random.choice([-1, 1, 2]))
    return ts


def build_query_params(query_type: str, table: str) -> str:
    if query_type == "SELECT":
        if table == "customers":
            return f'{{"city": "{random.choice(["Hanoi","HCMC","Da Nang","Hue"])}", "limit": {random.choice([10,20,50,100])}}}'
        elif table == "orders":
            return f'{{"status": "{random.choice(["pending","shipped","delivered"])}", "limit": {random.choice([10,20,50])}}}'
        elif table == "products":
            return f'{{"category": "{random.choice(["Electronics","Clothing","Books","Sports"])}", "limit": {random.choice([10,20,50])}}}'
        elif table == "inventory":
            return f'{{"warehouse_id": {random.randint(1,3)}, "limit": {random.choice([10,20,50])}}}'
    elif query_type == "INSERT":
        if table == "orders":
            return f'{{"customer_id": {random.randint(1,10000)}, "product_id": {random.randint(1,5000)}, "quantity": {random.randint(1,5)}}}'
        elif table == "inventory":
            return f'{{"product_id": {random.randint(1,5000)}, "quantity": {random.randint(10,100)}}}'
    elif query_type == "UPDATE":
        if table == "orders":
            return f'{{"order_id": {random.randint(1,50000)}, "status": "{random.choice(["confirmed","shipped","delivered"])}"}}'
        elif table == "inventory":
            return f'{{"product_id": {random.randint(1,5000)}, "delta": {random.randint(-10,10)}}}'
        elif table == "customers":
            return f'{{"customer_id": {random.randint(1,10000)}, "field": "address"}}'
    return '{}'


def generate_logs(n: int) -> list:
    base_date = datetime(2025, 4, 30, 23, 59, 59)
    logs = []
    num_users = 1000
    pattern_names = list(PATTERN_WEIGHTS.keys())
    pattern_probs = list(PATTERN_WEIGHTS.values())

    with tqdm(total=n, desc="Generating logs") as pbar:
        while len(logs) < n:
            user_id = random.randint(1, num_users)
            session_id = str(uuid.uuid4())[:16]
            pattern_name = random.choices(pattern_names, weights=pattern_probs)[0]
            pattern = SESSION_PATTERNS[pattern_name]

            # Vary session length: follow pattern 1-3 times with some noise
            repeats = random.randint(1, 3)
            session_queries = []
            for _ in range(repeats):
                session_queries.extend(pattern)
                # Insert occasional random query (noise)
                if random.random() < 0.15:
                    session_queries.append((
                        random.choice(QUERY_TYPES),
                        random.choice(TABLES),
                    ))

            session_start = sample_timestamp(base_date)
            for i, (qtype, table) in enumerate(session_queries):
                if len(logs) >= n:
                    break
                ts = session_start + timedelta(seconds=random.randint(1, 30) * (i + 1))
                logs.append({
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": user_id,
                    "session_id": session_id,
                    "query_type": qtype,
                    "table_name": table,
                    "query_params": build_query_params(qtype, table),
                    "site_origin": TABLE_SITE_MAP[table],
                    "pattern_type": pattern_name,
                })
                pbar.update(1)

    return logs


def save_logs(logs: list, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = ["timestamp", "user_id", "session_id", "query_type", "table_name",
                  "query_params", "site_origin", "pattern_type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(logs)
    print(f"Saved {len(logs):,} logs -> {path}")


if __name__ == "__main__":
    logs = generate_logs(QUERY_LOG_SIZE)
    save_logs(logs, LOGS_CSV)
    print("\nSample distribution:")
    from collections import Counter
    table_counts = Counter(r["table_name"] for r in logs)
    for t, c in sorted(table_counts.items()):
        print(f"  {t}: {c:,} ({c/len(logs)*100:.1f}%)")
