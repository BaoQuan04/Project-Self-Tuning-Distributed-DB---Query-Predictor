"""Populate Site A (customers, orders) and Site B (products, inventory) with Faker data."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import psycopg2
from faker import Faker
from tqdm import tqdm
from config.settings import SITE_A, SITE_B, NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS, NUM_INVENTORY_ITEMS

fake = Faker()
random.seed(42)
Faker.seed(42)

CATEGORIES = ["Electronics", "Clothing", "Books", "Sports", "Home", "Beauty", "Toys", "Food"]
BRANDS = ["Samsung", "Nike", "Apple", "Sony", "LG", "Adidas", "Xiaomi", "Dell", "HP", "Canon"]
ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]


def connect(cfg):
    return psycopg2.connect(**cfg)


def populate_site_a(conn):
    cur = conn.cursor()

    print(f"Inserting {NUM_CUSTOMERS} customers...")
    customers_batch = []
    for _ in tqdm(range(NUM_CUSTOMERS)):
        customers_batch.append((
            fake.name(),
            fake.unique.email(),
            fake.phone_number()[:20],
            fake.address()[:200],
            fake.city()[:100],
            fake.country()[:50],
        ))

    cur.executemany(
        "INSERT INTO customers (name, email, phone, address, city, country) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        customers_batch,
    )
    conn.commit()

    cur.execute("SELECT customer_id FROM customers")
    customer_ids = [r[0] for r in cur.fetchall()]

    print(f"Inserting {NUM_ORDERS} orders...")
    orders_batch = []
    for _ in tqdm(range(NUM_ORDERS)):
        qty = random.randint(1, 10)
        price = round(random.uniform(5.0, 2000.0), 2)
        orders_batch.append((
            random.choice(customer_ids),
            random.randint(1, NUM_PRODUCTS),
            qty,
            price,
            round(qty * price, 2),
            random.choice(ORDER_STATUSES),
        ))

    cur.executemany(
        "INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_price, status) VALUES (%s,%s,%s,%s,%s,%s)",
        orders_batch,
    )
    conn.commit()
    cur.close()
    print("Site A populated.")


def populate_site_b(conn):
    cur = conn.cursor()

    print(f"Inserting {NUM_PRODUCTS} products...")
    products_batch = []
    for i in tqdm(range(NUM_PRODUCTS)):
        products_batch.append((
            fake.catch_phrase()[:200],
            random.choice(CATEGORIES),
            random.choice(BRANDS),
            fake.text(max_nb_chars=200),
            round(random.uniform(5.0, 3000.0), 2),
            round(random.uniform(1.0, 5.0), 2),
        ))

    cur.executemany(
        "INSERT INTO products (name, category, brand, description, price, rating) VALUES (%s,%s,%s,%s,%s,%s)",
        products_batch,
    )
    conn.commit()

    cur.execute("SELECT product_id FROM products")
    product_ids = [r[0] for r in cur.fetchall()]

    print(f"Inserting {NUM_INVENTORY_ITEMS} inventory records...")
    inv_batch = []
    for pid in tqdm(product_ids):
        inv_batch.append((
            pid,
            random.randint(1, 3),
            random.randint(0, 500),
            random.randint(5, 50),
        ))

    cur.executemany(
        "INSERT INTO inventory (product_id, warehouse_id, quantity, reorder_level) VALUES (%s,%s,%s,%s)",
        inv_batch,
    )
    conn.commit()
    cur.close()
    print("Site B populated.")


if __name__ == "__main__":
    print("=== Populating Site A ===")
    with connect(SITE_A) as conn_a:
        populate_site_a(conn_a)

    print("\n=== Populating Site B ===")
    with connect(SITE_B) as conn_b:
        populate_site_b(conn_b)

    print("\nDone! Both sites populated.")
