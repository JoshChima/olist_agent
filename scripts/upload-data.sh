#!/usr/bin/env bash
# Uploads the Olist SQLite file to the private olist-data container, as you, through the
# toolbox's az sign-in (scripts/tf-toolbox.sh login). Terraform gave you Storage Blob
# Data Contributor there; shared keys are off, so it's Entra or nothing.
#
#   scripts/upload-data.sh [file]    default data/olist.sqlite (gitignored)
#
# The toolbox sees the repo at /w, so the file must be inside the repo. The next CD run
# loads it; to load it now, run CD again: gh workflow run cd.yml
set -euo pipefail
export MSYS_NO_PATHCONV=1 # stop Git Bash rewriting /w paths
cd "$(dirname "$0")/.."

file=$(realpath --relative-to=. "${1:-data/olist.sqlite}")
[ -f "$file" ] || { echo "upload-data: no file at $file" >&2; exit 1; }
case "$file" in
../* | /*) echo "upload-data: $file is outside the repo; copy it to data/ first" >&2; exit 1 ;;
esac

# `up` prints "UP <container> (<image>)"; whoami fails with a sign-in hint if needed.
name=$(scripts/tf-toolbox.sh up | cut -d' ' -f2)
scripts/tf-toolbox.sh whoami >/dev/null
x() { docker exec -w /w "$name" "$@"; }

account=$(x az storage account list --resource-group rg-olist-agent \
  --query "[?starts_with(name, 'stolistdata')].name | [0]" -o tsv)
[ -n "$account" ] || { echo "upload-data: no stolistdata* account yet; has CD applied infra/?" >&2; exit 1; }
x az storage blob upload --auth-mode login --account-name "$account" \
  --container-name olist-data --name olist.sqlite --file "$file" --overwrite --output none
echo "uploaded $file; run CD to load it: gh workflow run cd.yml"
