"""Download Terraform and tflint, verify their published SHA-256 sums, unpack to /usr/local/bin."""

import hashlib
import io
import os
import sys
import urllib.request
import zipfile

TF = os.environ["TERRAFORM_VERSION"]
TFLINT = os.environ["TFLINT_VERSION"]
TOOLS = [
    (
        "terraform",
        f"https://releases.hashicorp.com/terraform/{TF}/terraform_{TF}_linux_amd64.zip",
        f"https://releases.hashicorp.com/terraform/{TF}/terraform_{TF}_SHA256SUMS",
    ),
    (
        "tflint",
        f"https://github.com/terraform-linters/tflint/releases/download/v{TFLINT}/tflint_linux_amd64.zip",
        f"https://github.com/terraform-linters/tflint/releases/download/v{TFLINT}/checksums.txt",
    ),
]

for name, url, sums_url in TOOLS:
    data = urllib.request.urlopen(url).read()
    sums = urllib.request.urlopen(sums_url).read().decode()
    zip_name = url.rsplit("/", 1)[1]
    expected = next(line.split()[0] for line in sums.splitlines() if line.endswith(zip_name))
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        sys.exit(f"{zip_name}: checksum mismatch ({actual} != {expected})")
    zipfile.ZipFile(io.BytesIO(data)).extract(name, "/usr/local/bin")
    os.chmod(f"/usr/local/bin/{name}", 0o755)
    print(f"{name}: verified {zip_name}")
