-- Site B: products, inventory

CREATE TABLE IF NOT EXISTS products (
    product_id  SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    category    VARCHAR(100),
    brand       VARCHAR(100),
    description TEXT,
    price       NUMERIC(12, 2) NOT NULL,
    rating      NUMERIC(3, 2)  DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id  SERIAL PRIMARY KEY,
    product_id    INTEGER REFERENCES products(product_id),
    warehouse_id  INTEGER NOT NULL DEFAULT 1,
    quantity      INTEGER NOT NULL DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    last_updated  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category    ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand       ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_price       ON products(price);
CREATE INDEX IF NOT EXISTS idx_inventory_product_id ON inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse  ON inventory(warehouse_id);
