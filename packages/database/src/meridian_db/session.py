from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine_from_url(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, future=True)


def session_factory(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=create_engine_from_url(url), expire_on_commit=False, future=True)


@contextmanager
def session_scope(url: str) -> Iterator[Session]:
    factory = session_factory(url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
