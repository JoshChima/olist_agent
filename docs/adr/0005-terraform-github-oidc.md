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

## Amendment (2026-10-25): bootstrap state moves to Azure after the first apply
Local bootstrap state turned out to be a single point of loss: the only copy lived in a disposable Claude worktree, and the toolbox (ADR-0007) wrote to it on every apply.
- Bootstrap now has an `azurerm` backend: container `tfstate-bootstrap`, key `bootstrap.tfstate`, Entra-only auth. The storage account is passed as `-backend-config` at init, as in `infra/`.
- **That container is separate from `tfstate`.** Only the person running bootstrap gets Storage Blob Data Contributor on it. The `deploy` identity can write `tfstate`, but this state defines the CI identities' own permissions, so CI must not be able to edit it.
- **Local state is for the very first apply only,** before the storage account exists. A gitignored `local_override.tf` (Terraform's override-file mechanism) forces `backend "local"`, and `terraform init -migrate-state` then moves the state into the container.
- Blob versioning and soft delete on the storage account now protect bootstrap state too.
