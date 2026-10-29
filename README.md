# olist_agent

A time-travel simulator over the [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), with multi-agent AI on top. It runs on Azure Container Apps, is provisioned with Terraform, and deploys through GitHub Actions.

**Status: P0, the walking skeleton.** A FastAPI app with `/health` and `/api/hello` serves a React shell, and every merge to `main` deploys it.

```
app/                FastAPI (uv) + React/Vite SPA (pnpm), one container
  olist_agent/      Python package
  web/              SPA; built into web/dist and served by FastAPI
infra/bootstrap/    one-time, local state: tfstate storage, app RG, CI identities
infra/              everything else; applied by CD
.github/workflows/  ci.yml (PRs), cd.yml (main)
```

## Local development

```bash
docker compose up --build     # http://localhost:8080 serves the SPA, /health and /api/hello
```

Or run the two halves with hot reload:

```bash
cd app && uv run uvicorn olist_agent.main:app --reload --port 8080
cd app/web && pnpm install && pnpm dev    # http://localhost:5173, proxies /api to :8080
```

Checks (the same ones CI runs): `cd app && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`.

## First deploy (one time, by you)

You need `az`, `gh`, `terraform` >= 1.10, and an Azure subscription where you are **Owner**. Owner is required because bootstrap creates role assignments and a custom role.

1. **Create the GitHub repo**, but don't push `main` yet: CD would run before its variables exist.
   ```bash
   gh repo create <owner>/olist_agent --public --source . --remote origin
   ```
2. **Sign in to Azure** and select the subscription.
   ```bash
   az login
   az account set --subscription <subscription-id>
   ```
3. **Bootstrap.** This creates the state storage, the app resource group, and the two OIDC identities, and registers the resource providers. It takes about 2 minutes. The storage that bootstrap's own state will live in doesn't exist yet, so the first apply runs on local state, and the state moves into Azure afterwards.
   ```bash
   printf 'terraform {\n  backend "local" {}\n}\n' > infra/bootstrap/local_override.tf  # gitignored
   terraform -chdir=infra/bootstrap init
   terraform -chdir=infra/bootstrap apply -var github_repository=<owner>/olist_agent \
     -var github_sub_prefix="$(gh api repos/<owner>/olist_agent/actions/oidc/customization/sub --jq .sub_claim_prefix)"
   ```
   Then move the state into the `tfstate-bootstrap` container, which only you can access, and delete the local copy once it's confirmed. Read the storage account name *before* removing the override: once it's gone, `terraform output` fails with "Backend initialization required".
   ```bash
   account="$(terraform -chdir=infra/bootstrap output -raw tfstate_storage_account)"
   rm infra/bootstrap/local_override.tf
   terraform -chdir=infra/bootstrap init -migrate-state -backend-config=storage_account_name="$account"
   terraform -chdir=infra/bootstrap state list   # now read from Azure
   ```
   Later bootstrap runs go through `scripts/tf-toolbox.sh` (see Running Terraform locally).
4. **Configure the repo.** Print the generated `gh secret set` / `gh variable set` commands and run them. Workflows read the secrets, because GitHub masks secrets in this public repo's logs and never masks variables. `scripts/tf-toolbox.sh` reads the variables, which only collaborators can see.
   ```bash
   terraform -chdir=infra/bootstrap output -raw github_variables_commands
   ```
   Then add two more secrets: the budget alert address, and your Entra object ID, which makes you a Postgres admin and lets you upload data.
   ```bash
   gh secret set BUDGET_ALERT_EMAIL -R <owner>/olist_agent --body you@example.com
   gh secret set AZURE_OPERATOR_OBJECT_ID -R <owner>/olist_agent --body "$(az ad signed-in-user show --query id -o tsv)"
   ```
5. **Push `main`.** CD applies `infra/`. The first run takes about 5–10 minutes, mostly for the Container Apps environment. It then builds and pushes the image, rolls the app, and smoke-tests `/health`.
   If this work is still on a feature branch, merge it into `main` first.
   ```bash
   git push -u origin main
   ```
6. **Protect `main`** (recommended). Require the CI checks `app`, `web`, `iac` and `plan` before merging. CD applies whatever lands on `main`, so CI is the only gate.

To check it worked: the CD log ends with `live: <sha>`, the app URL (`terraform -chdir=infra output app_url`, or the CD log) serves the shell, and `budget-olist-agent` appears under Cost Management → Budgets.

Optional: to run a plan from your machine (bootstrap gave you blob access to the state):

```bash
terraform -chdir=infra init -backend-config=storage_account_name=<tfstate_storage_account output>
terraform -chdir=infra plan -var budget_alert_email=you@example.com -var operator_object_id=<your object ID>
```

## Uploading data

The deployed app shows "no data loaded yet" until you upload the Kaggle `olist.sqlite`. Put it in `data/` (gitignored), sign in to the toolbox, and upload it:

```bash
scripts/tf-toolbox.sh login         # once per toolbox container
scripts/upload-data.sh              # or: scripts/upload-data.sh data/other.sqlite
gh workflow run cd.yml              # CD's loader job loads it
```

The file goes to the private `olist-data` container, as you. CD runs the loader job after every deploy. The job loads only when the file or the migrations changed, and fails CD if it fails.

## How the pieces fit

- **Two Terraform roots.** Bootstrap creates what the pipeline needs before it can run: the state backend, plus the identity it logs in as. Nothing in `infra/` can do that for itself.
- **OIDC, no secrets.** GitHub mints a short-lived token per job, and Azure trusts it only for a matching subject. There are two identities:
  - `deploy` is trusted only on `refs/heads/main` and applies `infra/`.
  - `plan` is trusted only for `pull_request`. It can't change anything, but it can read, and that includes container-app secrets (see the table below).

  Fork PRs get no token at all. The exact roles are in the table under Bootstrap role assignments.
- **Logs and PR comments are public.** Workflows read Azure IDs from secrets, and Terraform output goes through `scripts/redact.py`, which fails the job if an ID survives redaction. For agents, the `scripts/guard_ids.py` hook blocks GitHub and Linear posts that contain a known ID.
- **Workload-profiles environment from day one.** P5's serverless GPU needs it, and an environment can't be converted after it's created.
- **Terraform owns infrastructure; CD owns the image.** The container app ignores changes to `image`. The first apply runs a public placeholder that also listens on 8080, and every deploy after that is `az containerapp update --image <acr>/olist-agent:<sha>`. The loader job works the same way, and CD runs it after each deploy.
- **Cost.** ACR Basic is about $5 a month. The app scales to zero, Log Analytics is capped at 1 GB a day, and an RG budget alerts at 80% actual and 100% forecast of $50. A budget alerts but never stops spending.

## Bootstrap role assignments

Every role assignment `infra/bootstrap/main.tf` creates, with the reason from its code comments. The app RG is `rg-olist-agent`; `tfstate` and `tfstate-bootstrap` are containers in the state storage account.

| Principal | Role | Scope | Why |
|---|---|---|---|
| deploy identity | Contributor | app RG | Creates and changes the app's resources when CD applies `infra/`. |
| deploy identity | Role Based Access Control Administrator, with an ABAC condition | app RG | Terraform grants roles (e.g. AcrPull to the app's identity), which Contributor can't do. User Access Administrator could, but could also make itself Owner. The condition lets this identity grant or revoke **only** AcrPull, Storage Blob Data Reader and Storage Blob Data Contributor. |
| deploy identity | Storage Blob Data Contributor | `tfstate` container | Reads, writes and locks the `infra/` state. It has nothing on `tfstate-bootstrap`: CI must never be able to edit the state that defines its own access. |
| plan identity | Reader | app RG | A PR branch runs whatever code it contains, so plan must not be able to change anything. |
| plan identity | Custom role `olist-agent terraform plan: list container app secrets` (defined in bootstrap, assignable only in the app RG; two actions, `Microsoft.App/containerApps/listSecrets/action` and `Microsoft.App/jobs/listSecrets/action`) | app RG | The azurerm provider calls listSecrets when it refreshes a container app or a container app job, and Reader doesn't include those actions, so plan would fail without them. This means the plan identity **can read container-app and job secrets**; it is not read-only in the strict sense. |
| plan identity | Storage Blob Data Reader | `tfstate` container | Reads the `infra/` state. CI runs plan with `-lock=false`, because taking the lock (a blob lease) is a write. |
| you (the developer) | Storage Blob Data Contributor | `tfstate-bootstrap` container | Bootstrap's own state. Only you can read or write it; the CI identities can't, because this state describes their permissions. |
| you (the developer) | Storage Blob Data Contributor | `tfstate` container | Owner is a control-plane role and doesn't include reading blobs. You need this to run `terraform plan` against the remote state from your machine. |

## Running Terraform locally

Run Terraform against real Azure through the toolbox container rather than your host's Terraform. The container only uses IPv4, uses the same tool versions as CI, and leaves your `az` login on the host untouched (ADR-0007). You need Docker and `gh`, and you run it from Git Bash:

```bash
scripts/tf-toolbox.sh up              # build the image if needed and start the container
scripts/tf-toolbox.sh check infra     # fmt, validate, tflint, terraform test; drift too once signed in
scripts/tf-toolbox.sh check infra --offline  # the same static checks, never contacting Azure
scripts/tf-toolbox.sh login           # device-code sign-in; then check also looks for drift
scripts/tf-toolbox.sh plan bootstrap  # plan + risk table + PLAN_SHA256
scripts/tf-toolbox.sh apply bootstrap /tmp/plans/bootstrap.tfplan <sha256>
scripts/tf-toolbox.sh down            # az logout and remove the container
```

To plan `infra`, first export `TF_VAR_budget_alert_email` and `TF_VAR_operator_object_id`. They're GitHub secrets, so the script can't read them back. `apply` only accepts `bootstrap`: `infra/` is applied by CD. In Claude Code, the `terraform-operator` subagent runs these commands for you and asks before every apply.

### Why apply needs the plan's sha256

`terraform plan -out=file` saves the plan to a file, and `terraform apply file` carries out exactly that file. This splits reviewing a change from making it: you read the plan first, then apply what you read. Terraform also refuses the file if the state has moved since the plan was made, so a stale plan can't be applied by accident.

That check doesn't say *which* plan the file is. Inside the container, an agent could run `plan` again and overwrite the file after you reviewed it, and Terraform would apply the new one without complaint. The bytes applied might not be the bytes you reviewed.

The sha256 closes that gap. It's a fingerprint of the file's exact bytes: change one character and it changes completely. `plan` prints it next to the risk table, and you approve that value. `apply` recomputes the hash of the file and refuses if it differs, then re-runs the risk gate on that same file before applying. Approval and apply are tied to the same bytes, so an agent can't swap the plan, and can't approve its own: the hash it was given has to be the one you approved.

Bootstrap is where this matters most. A half-landed apply left state and Azure disagreeing and broke CI's plans (ADR-0007), and bootstrap defines CI's own permissions, so a wrong apply there can change what CI is allowed to do. Nothing else applies it, so this check is the gate.

## Teardown

```bash
terraform -chdir=infra destroy -var budget_alert_email=you@example.com -var operator_object_id=<your object ID>
```

The state storage has `prevent_destroy` set on purpose. To remove bootstrap too, delete that lifecycle block first, then run `terraform -chdir=infra/bootstrap destroy -var github_repository=<owner>/olist_agent -var github_sub_prefix=<same as apply>`.

## License and attribution

The code is [MIT](LICENSE).

This project uses the **Brazilian E-Commerce Public Dataset by Olist** and the **Marketing Funnel by Olist** dataset, published on Kaggle by [Olist](https://olist.com) under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/):

- <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>
- <https://www.kaggle.com/datasets/olistbr/marketing-funnel-olist>

The dataset isn't included in this repo. Any derived data that contains review text (golden sets, fixtures) lives under `data/` with its own CC BY-NC-SA 4.0 license ([data/LICENSE](data/LICENSE)), and is non-commercial.
