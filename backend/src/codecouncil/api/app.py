"""FastAPI application factory for CodeCouncil."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the CodeCouncil FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ------------------------------------------------------------------ #
        # Startup
        # ------------------------------------------------------------------ #
        logger.info("CodeCouncil API starting up…")

        # Database engine + session factory
        try:
            from codecouncil.db.engine import create_engine, create_session_factory
            engine = create_engine(os.environ.get("DATABASE_URL"))
            session_factory = create_session_factory(engine)
            app.state.db_engine = engine
            app.state.db_session_factory = session_factory
            logger.info("Database engine initialised.")
        except Exception as exc:
            logger.warning("Database not available (%s) — running without persistence.", exc)
            app.state.db_engine = None
            app.state.db_session_factory = None

        # EventBus
        from codecouncil.events.bus import EventBus
        app.state.event_bus = EventBus()

        # ProviderRegistry (populated lazily — no credentials needed at boot)
        from codecouncil.providers.registry import ProviderRegistry
        app.state.provider_registry = ProviderRegistry()

        # AgentRegistry (empty at boot; populated per-run)
        from codecouncil.agents.registry import AgentRegistry
        app.state.agent_registry = AgentRegistry()

        logger.info("CodeCouncil API ready.")
        yield

        # ------------------------------------------------------------------ #
        # Shutdown
        # ------------------------------------------------------------------ #
        logger.info("CodeCouncil API shutting down…")
        if app.state.db_engine is not None:
            await app.state.db_engine.dispose()
            logger.info("Database engine disposed.")

    app = FastAPI(
        title="CodeCouncil",
        description="AI agent council for codebase intelligence",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    from codecouncil.api.middleware import add_middleware
    add_middleware(app)

    # Routers
    from codecouncil.api.routes import agents, config, health, personas, providers, runs, sessions
    app.include_router(runs.router,      prefix="/api")
    app.include_router(config.router,    prefix="/api")
    app.include_router(personas.router,  prefix="/api")
    app.include_router(agents.router,    prefix="/api")
    app.include_router(providers.router, prefix="/api")
    app.include_router(sessions.router,  prefix="/api")
    app.include_router(health.router,    prefix="/api")

    # Prometheus metrics
    from codecouncil.api.metrics import metrics_endpoint
    app.add_route("/metrics", metrics_endpoint)

    # WebSocket
    from codecouncil.api.websocket import websocket_debate
    app.add_api_websocket_route("/ws/runs/{run_id}/debate", websocket_debate)

    # SSE
    from codecouncil.api.sse import sse_stream
    app.add_api_route("/api/runs/{run_id}/stream", sse_stream, methods=["GET"])

    return app
