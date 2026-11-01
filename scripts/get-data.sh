#!/usr/bin/env bash
# Downloads the Olist SQLite build from Kaggle into data/olist.sqlite, unless it's there.
# The Kaggle CLI signs in with whatever it finds (kaggle auth login, KAGGLE_API_TOKEN,
# ~/.kaggle) and downloads this public dataset anonymously if it finds nothing.
#
#   scripts/get-data.sh
#
# Needs uv. Prints the manual steps and exits 1 if Kaggle won't hand the file over.
set -euo pipefail
cd "$(dirname "$0")/.."

dataset=terencicp/e-commerce-dataset-by-olist-as-an-sqlite-database
file=data/olist.sqlite
[ ! -f "$file" ] || { echo "get-data: $file is already there"; exit 0; }

# kaggle 2.2.5 imports six without depending on it.
kaggle=(uvx -q --with six kaggle@2.2.5)
tmp=$(mktemp -d data/.download.XXXXXX)
trap 'rm -rf "$tmp"' EXIT
if ! "${kaggle[@]}" datasets download "$dataset" -p "$tmp" --unzip >&2 ||
  [ ! -f "$tmp/olist.sqlite" ]; then
  cat >&2 <<EOF
get-data: the Kaggle download failed. Sign in and retry:
  ${kaggle[*]} auth login
Or download it by hand:
  1. https://www.kaggle.com/datasets/$dataset (Download)
  2. unzip it and put olist.sqlite at $file
EOF
  exit 1
fi
mv "$tmp/olist.sqlite" "$file"
echo "get-data: downloaded $file"
