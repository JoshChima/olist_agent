import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Baked into the image at build time (see Dockerfile), so the CD smoke test can
# prove the revision serving traffic is the commit it just pushed.
VERSION = os.getenv("GIT_SHA", "dev")

app = FastAPI(title="olist_agent")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "Hello from olist_agent"}


# Mounted last so API routes win. Absent when running tests or API-only dev.
static_dir = Path(os.getenv("STATIC_DIR", "web/dist"))
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="spa")
