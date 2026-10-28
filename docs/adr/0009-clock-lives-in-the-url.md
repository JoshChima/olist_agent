# 9. The clock lives in the URL, not in a server session

Date: 2026-10-27 · Status: Accepted

ADR-0001 gives each browser session its own clock, but doesn't say where the clock is stored. We keep it in the page URL as a query parameter (`?clock=2017-11-24`), mirrored to localStorage so a return visit resumes where it left off. Every API call carries the clock explicitly, so the server holds no session state. A server-side session row keyed by a cookie was rejected: it adds a table, a cookie and a cleanup job, and the URL version gives shareable links ("look at Black Friday") for free. The cost is that the clock is client-supplied, so the API validates it on every request and rejects one outside the dataset's range instead of silently clamping it.
