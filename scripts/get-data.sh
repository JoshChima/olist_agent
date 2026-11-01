#!/usr/bin/env bash
# Downloads the Olist SQLite build from Kaggle into data/olist.sqlite, unless it's there.
# The Kaggle CLI signs in with KAGGLE_API_TOKEN (from your shell, else from .env; see
# .env.example) or whatever else it finds (kaggle auth login, ~/.kaggle), and downloads
# this public dataset anonymously if it finds nothing.
#
#   scripts/get-data.sh
#
# Needs uv. Prints the manual steps and exits 1 if Kaggle won't hand the file over.
set -euo pipefail
cd "$(dirname "$0")/.."

dataset=terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database
file=data/olist.sqlite
if [ -f "$file" ]; then
  echo "get-data: $file is already there"
  exit 0
fi
# CRs stripped, so a .env saved on Windows doesn't put one at the end of the token.
# shellcheck source=/dev/null
[ -n "${KAGGLE_API_TOKEN:-}" ] || [ ! -f .env ] || { set -a; . <(tr -d '\r' <.env); set +a; }

# ponytail: kaggle 2.2.5 imports six without depending on it; drop --with once it does.
kaggle=(uvx -q --with six==1.17.0 kaggle@2.2.5)
tmp=$(mktemp -d data/.download.XXXXXX)
trap 'rm -rf "$tmp"' EXIT
if ! "${kaggle[@]}" datasets download "$dataset" -p "$tmp" --unzip >&2 ||
  [ ! -f "$tmp/olist.sqlite" ]; then
  cat >&2 <<EOF
get-data: the Kaggle download failed. Set KAGGLE_API_TOKEN in .env (see .env.example;
the token is on kaggle.com > Settings > API) and retry. Or download it by hand:
  1. https://www.kaggle.com/datasets/$dataset (Download)
  2. unzip it and put olist.sqlite at $file
EOF
  exit 1
fi
mv "$tmp/olist.sqlite" "$file"
echo "get-data: downloaded $file"
