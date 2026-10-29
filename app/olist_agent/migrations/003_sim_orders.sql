-- as_of views read the clock (a day, D) from the transaction-local setting sim.clock and show
-- rows whose governing timestamp is before D+1 at 00:00 (ADR-0008, GLOSSARY.md "Clock").
-- With no clock set, current_setting returns NULL, or '' once a SET LOCAL has ended, and
-- the comparison is NULL: no rows.

-- Repaired timestamps (GLOSSARY.md): each order's lifecycle clamped so no stage is earlier
-- than the one before it. The loader rebuilds it from raw.orders, which keeps the originals.
CREATE TABLE IF NOT EXISTS raw.order_lifecycle (
    order_id text,
    order_approved_at timestamp,
    order_delivered_carrier_date timestamp,
    order_delivered_customer_date timestamp,
    repaired boolean
);

-- Lifecycle fields later than the clock read as NULL, and order_status is the derived
-- status (GLOSSARY.md). The estimated delivery date is known at purchase, so it shows.
CREATE OR REPLACE VIEW sim.orders AS
SELECT
    o.order_id,
    o.customer_id,
    CASE
        WHEN o.order_status IN ('canceled', 'unavailable')
            AND o.order_estimated_delivery_date < c.day_end THEN o.order_status
        WHEN l.order_delivered_customer_date < c.day_end THEN 'delivered'
        WHEN l.order_delivered_carrier_date < c.day_end THEN 'shipped'
        WHEN l.order_approved_at < c.day_end THEN 'approved'
        ELSE 'purchased'
    END AS order_status,
    o.order_purchase_timestamp,
    CASE WHEN l.order_approved_at < c.day_end THEN l.order_approved_at END
        AS order_approved_at,
    CASE WHEN l.order_delivered_carrier_date < c.day_end THEN l.order_delivered_carrier_date END
        AS order_delivered_carrier_date,
    CASE WHEN l.order_delivered_customer_date < c.day_end THEN l.order_delivered_customer_date END
        AS order_delivered_customer_date,
    o.order_estimated_delivery_date,
    l.repaired
FROM raw.orders o
JOIN raw.order_lifecycle l USING (order_id)
CROSS JOIN (SELECT nullif(current_setting('sim.clock', true), '')::date + 1) c(day_end)
WHERE o.order_purchase_timestamp < c.day_end;

-- Items and payments are governed by their order's purchase. Their own dates (the shipping
-- limit) are known at purchase, so they show.
CREATE OR REPLACE VIEW sim.order_items AS
SELECT * FROM raw.order_items WHERE order_id IN (SELECT order_id FROM sim.orders);

CREATE OR REPLACE VIEW sim.order_payments AS
SELECT * FROM raw.order_payments WHERE order_id IN (SELECT order_id FROM sim.orders);
