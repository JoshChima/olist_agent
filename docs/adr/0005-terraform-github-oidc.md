# 5. Terraform with GitHub Actions OIDC and bootstrapped remote state

Date: 2026-10-18 · Status: Accepted

## Context
The infrastructure must be code from day one. Every phase has to end deployed, and each phase's infrastructure change should be visible in the CI/CD history. Terraform was chosen over Bicep. Long-lived cloud credentials stored in GitHub are a liability.

## Decision
- `infra/bootstrap/` creates the state storage account. It uses local state and the user runs it once, because the configuration that creates the state backend cannot also store its state there.
- `infra/` uses the azurerm remote backend in that storage account.
- GitHub Actions authenticates to Azure through OIDC federated credentials, so no client secrets exist.
- There is one Azure environment, in East US:
  - **On a pull request:** lint, tests, evals, tflint, trivy, and a `terraform plan` posted as a PR comment.
  - **On merge to `main`:** `terraform apply`, image build and push, deploy, and a smoke test.
- An Azure consumption budget alert is part of the Terraform configuration.

## Consequences
- The bootstrap step is manual and documented in the README.
- There are no per-PR preview environments, which keeps cost down. The module layout should still allow adding `staging` later.
- The pipeline identity needs carefully scoped role assignments. Too broad is a security risk; too narrow breaks `apply`.
