-- as_of views read the clock (a day, D) from the transaction-local setting sim.clock and show
-- rows whose governing timestamp is before D+1 at 00:00 (ADR-0008, GLOSSARY.md "Clock").
-- With no clock set, current_setting returns NULL, or '' once a SET LOCAL has ended, and
-- the comparison is NULL: no rows.

CREATE OR REPLACE VIEW sim.orders AS
SELECT *
FROM raw.orders
WHERE order_purchase_timestamp < nullif(current_setting('sim.clock', true), '')::date + 1;
