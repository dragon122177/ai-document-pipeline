from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import auth, documents, events, jobs, operations, reviews, search
from .config import Settings
from .database import Database
from .events import EventBroker
from .intelligence import LocalIntelligenceProvider, RemoteJsonProvider
from .pipeline import PipelineProcessor, PipelineWorker
from .seed import seed_database
from .services import Services
from .storage import LocalFileStorage
from .utils import utc_now


def create_app(
    settings: Settings | None = None,
    *,
    start_worker: bool | None = None,
) -> FastAPI:
    resolved = settings or Settings()
    logging.basicConfig(
        level=getattr(logging, resolved.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    database = Database(resolved.database_path)
    database.initialize()
    seed_database(database)
    storage = LocalFileStorage(
        resolved.upload_directory, resolved.max_upload_bytes
    )
    broker = EventBroker()
    provider = (
        RemoteJsonProvider(resolved.remote_ai_url, resolved.remote_ai_token)
        if resolved.remote_ai_url
        else LocalIntelligenceProvider()
    )
    processor = PipelineProcessor(
        database,
        provider,
        broker,
        stage_delay=resolved.pipeline_stage_delay,
    )
    worker = PipelineWorker(processor, resolved.worker_poll_interval)
    should_start_worker = (
        resolved.worker_enabled if start_worker is None else start_worker
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        del application
        if should_start_worker:
            worker.start()
        try:
            yield
        finally:
            worker.stop()
            database.close()

    app = FastAPI(
        title="DocuFlux AI Document Pipeline",
        version="1.0.0",
        summary="Secure document ingestion, extraction, redaction, and review.",
        lifespan=lifespan,
    )
    app.state.services = Services(
        settings=resolved,
        database=database,
        storage=storage,
        broker=broker,
        processor=processor,
        worker=worker,
        provider_name=provider.name,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved.web_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        del request
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "The request payload is invalid.",
                    "details": error.errors(),
                }
            },
        )

    @app.get("/", tags=["system"])
    def root() -> dict[str, str]:
        return {
            "name": "DocuFlux AI Document Pipeline",
            "version": "1.0.0",
            "docs": "/docs",
        }

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, object]:
        check = database.fetch_one("SELECT 1 AS ok")
        return {
            "status": "healthy" if check else "degraded",
            "version": "1.0.0",
            "database": "sqlite",
            "provider": provider.name,
            "worker": {
                "enabled": should_start_worker,
                "running": worker.running,
            },
            "time": utc_now(),
        }

    app.include_router(auth.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(search.router, prefix="/api")
    app.include_router(operations.router, prefix="/api")
    app.include_router(events.router, prefix="/api")
    return app


app = create_app()
