import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import Scope

# Baked into the image at build time (see Dockerfile), so the CD smoke test can
# prove the revision serving traffic is the commit it just pushed.
VERSION = os.getenv("GIT_SHA", "dev")

# ADR-0006 picks the Azure Monitor exporter. Gating it on the env var keeps local
# runs Azure-free. Configured before the app is created so FastAPI gets instrumented.
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor

    configure_azure_monitor()

app = FastAPI(title="olist_agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from olist_agent"}


class SPAStaticFiles(StaticFiles):
    """Serves index.html for unknown paths so client-side routes deep-link."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            # Unknown /api/* and missing files (/assets/old-hash.js) stay a 404
            # rather than returning the SPA shell. Only extensionless routes fall back.
            p = Path(path)
            if e.status_code != 404 or p.parts[:1] == ("api",) or p.suffix:
                raise
            return await super().get_response("index.html", scope)


# Mounted last so API routes win. Absent when running tests or API-only dev.
static_dir = Path(os.getenv("STATIC_DIR", "web/dist"))
if static_dir.is_dir():
    app.mount("/", SPAStaticFiles(directory=static_dir, html=True), name="spa")
