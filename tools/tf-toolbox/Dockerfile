# Terraform + Azure CLI toolbox for running against real Azure from a dev machine
# (scripts/tf-toolbox.sh). Containers here only get IPv4, which sidesteps the
# local network's IPv6 resets to Azure.
#
# Built on Docker Hub's python image, not mcr.microsoft.com/azure-cli: pulls from
# MCR fail over IPv6 on that same network. CI's static checks run in this image too
# (scripts/check.sh). Keep TERRAFORM_VERSION equal to setup-terraform's in ci.yml's
# plan job and cd.yml.
FROM python:3.12-slim

ARG AZURE_CLI_VERSION=2.90.0
ARG TERRAFORM_VERSION=1.16.6
ARG TFLINT_VERSION=0.64.0

RUN pip install --no-cache-dir --root-user-action=ignore "azure-cli==${AZURE_CLI_VERSION}"

COPY install.py /tmp/install.py
RUN TERRAFORM_VERSION=${TERRAFORM_VERSION} TFLINT_VERSION=${TFLINT_VERSION} python /tmp/install.py \
    && rm /tmp/install.py

RUN useradd --create-home --uid 10001 tf
USER tf

# Keep provider plugins inside the container, away from the Windows checkout's .terraform/.
ENV TF_DATA_DIR=/tmp/tfdata \
    TF_IN_AUTOMATION=1 \
    AZURE_CORE_COLLECT_TELEMETRY=no
