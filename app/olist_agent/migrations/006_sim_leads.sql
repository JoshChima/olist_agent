-- The marketing funnel's tables as of the clock (see 003 for how views read it).

-- An MQL appears on its first contact.
CREATE OR REPLACE VIEW sim.leads_qualified AS
SELECT *
FROM raw.leads_qualified
WHERE first_contact_date < nullif(current_setting('sim.clock', true), '')::date + 1;

-- A closed deal appears when it's won.
CREATE OR REPLACE VIEW sim.leads_closed AS
SELECT *
FROM raw.leads_closed
WHERE won_date < nullif(current_setting('sim.clock', true), '')::date + 1;
