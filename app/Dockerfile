# Stage 1: build the SPA. Node never reaches the runtime image.
FROM node:24-alpine AS web
WORKDIR /web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

# Stage 2: runtime. Deps are installed before the source is copied so code
# edits don't invalidate the (slow) dependency layer.
FROM python:3.13-slim
# uv installs everything, so the base image's pip (and its vendored, CVE-prone
# urllib3/setuptools) is dead weight that fails the trivy image scan.
RUN pip uninstall -y pip
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
COPY olist_agent ./olist_agent
COPY --from=web /web/dist ./web/dist

ARG GIT_SHA=dev
ENV GIT_SHA=$GIT_SHA

# Numeric UID so Kubernetes-style runAsNonRoot checks can verify it.
RUN useradd --system --uid 10001 app
USER 10001
# 8080, not 80: non-root can't bind ports <1024, and the Terraform placeholder
# image (aspnetapp) also listens on 8080, so ingress works before our first push.
EXPOSE 8080
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
CMD ["uvicorn", "olist_agent.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
