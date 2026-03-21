"""FastAPI dependencies."""
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession | None, None]:
    """Yield a DB session from the app's session factory.

    If the database is not configured (e.g. in tests), yields ``None``.
    """
    session_factory = getattr(request.app.state, "db_session_factory", None)
    if session_factory is None:
        yield None
        return
    async with session_factory() as session:
        yield session
