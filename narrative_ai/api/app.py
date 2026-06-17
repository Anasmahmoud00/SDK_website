"""
Narrative AI SDK Developer Portal Server.

A simplified server hosting the static SDK Documentation Portal.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)


def create_app(engines: list[str] | None = None) -> FastAPI:
    """Create a simple FastAPI app to serve the static documentation portal."""
    app = FastAPI(
        title="Narrative AI SDK Developer Portal",
        description="Documentation website for Narrative AI SDK",
        version="1.0.0",
    )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "message": "Docs Portal Server is running",
        }

    @app.get("/")
    @app.get("/docs-portal")
    async def root():
        template_path = os.path.join(os.path.dirname(__file__), "templates", "docs_portal.html")
        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        
        # Check parent folder as fallback
        parent_docs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs_portal.html")
        if os.path.exists(parent_docs_path):
            with open(parent_docs_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
                
        return HTMLResponse(content="<h1>Narrative AI SDK Developer Portal</h1><p>Template not found</p>")

    return app


def _app_factory() -> FastAPI:
    """Factory for uvicorn multi-worker/reload mode."""
    return create_app()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Narrative AI SDK Developer Portal Server",
    )
    parser.add_argument(
        "--engines",
        default="stt,tts,llm,rag,vlm,ingestion",
        help="Comma-separated list of engines (kept for CLI compatibility)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers (default: 1)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Starting Narrative AI SDK Developer Portal Server...")

    import uvicorn

    if args.reload or args.workers > 1:
        uvicorn.run(
            "narrative_ai.api.app:_app_factory",
            factory=True,
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
        )
    else:
        app = create_app()
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()
