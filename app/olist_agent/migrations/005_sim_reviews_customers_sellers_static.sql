-- The rest of the non-funnel tables as of the clock (see 003 for how views read it), and
-- the static tables, which have no time dimension.

-- Governed by review_creation_date. The answer stays NULL until the clock passes it.
-- review_id isn't unique: a review is (review_id, order_id).
CREATE OR REPLACE VIEW sim.order_reviews AS
SELECT
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    CASE
        WHEN review_answer_timestamp < nullif(current_setting('sim.clock', true), '')::date + 1
        THEN review_answer_timestamp
    END AS review_answer_timestamp
FROM raw.order_reviews
WHERE review_creation_date < nullif(current_setting('sim.clock', true), '')::date + 1;

-- customer_id is per order, so a customer appears with their order's purchase. A person is
-- customer_unique_id (GLOSSARY.md "Person").
CREATE OR REPLACE VIEW sim.customers AS
SELECT c.*
FROM raw.customers c
WHERE EXISTS (
    SELECT FROM raw.orders o
    WHERE o.customer_id = c.customer_id
        AND o.order_purchase_timestamp < nullif(current_setting('sim.clock', true), '')::date + 1
);

-- A seller's first activity: the earlier of their first order's purchase and their closed
-- deal's won_date. Computed once per load: the loader refreshes it after the raw tables.
CREATE MATERIALIZED VIEW IF NOT EXISTS raw.seller_first_activity AS
SELECT seller_id, min(at) AS first_active_at
FROM (
    SELECT i.seller_id, o.order_purchase_timestamp AS at
    FROM raw.order_items i
    JOIN raw.orders o USING (order_id)
    UNION ALL
    SELECT seller_id, won_date FROM raw.leads_closed
) a
WHERE seller_id IS NOT NULL
GROUP BY seller_id;

CREATE OR REPLACE VIEW sim.sellers AS
SELECT s.*
FROM raw.sellers s
JOIN raw.seller_first_activity f USING (seller_id)
WHERE f.first_active_at < nullif(current_setting('sim.clock', true), '')::date + 1;

-- Static tables: always fully visible, clock or no clock.
CREATE OR REPLACE VIEW sim.products AS SELECT * FROM raw.products;
CREATE OR REPLACE VIEW sim.geolocation AS SELECT * FROM raw.geolocation;
CREATE OR REPLACE VIEW sim.product_category_name_translation AS
SELECT * FROM raw.product_category_name_translation;
