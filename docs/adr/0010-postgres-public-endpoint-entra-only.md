# 10. Postgres on a public endpoint with Entra-only auth

Date: 2026-10-27 · Status: Accepted

## Context
- The Container Apps environment (ADR-0004) was created without a VNet. Private access to Postgres would mean recreating the environment, and with it the app's URL.
- A private endpoint also adds a VNet, a private DNS zone and their cost to a ~$30–50/month project.
- Without a VNet, Container Apps calls arrive from shared Azure outbound IPs. So the firewall must admit all Azure-hosted traffic ("allow Azure services"), and that includes other tenants.

## Decision
- Postgres Flexible Server gets a public endpoint, TLS only, and the "allow Azure services" firewall rule, with no other IP ranges. Local development uses Postgres in docker-compose instead.
- **Entra ID authentication only. Password auth is disabled, so there is no password to leak or rotate.**
  - The loader job's managed identity is the server's Entra admin. It creates the app's managed identity as a role that can only read the `sim` schema (ADR-0008).
  - The developer's own Entra user is a second admin, set through a Terraform variable, for debugging through the toolbox.

## Consequences
- Anyone on Azure can reach the port. Without a valid Entra token for one of the admin or app identities, they can't sign in.
- The app and the loader fetch short-lived tokens with `azure-identity` and refresh them before they expire (about an hour). Local development uses a password DSN, so connection setup has two paths.
- If the project later needs private networking, that means a new VNet-integrated environment, recorded in a new ADR.
