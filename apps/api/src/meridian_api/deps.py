from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from meridian_config.settings import get_settings
from meridian_db.models import User
from meridian_db.session import session_factory
from sqlalchemy.orm import Session

from meridian_api.session_token import read_token

COOKIE = "meridian_session"


def db_session() -> Iterator[Session]:
    factory = session_factory(get_settings().database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def current_user(request: Request, db: Session = Depends(db_session)) -> User:
    token = request.cookies.get(COOKIE)
    user_id = read_token(token) if token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sign in to use this desk.")
    try:
        parsed = uuid.UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Sign in to use this desk.") from exc
    user = db.get(User, parsed)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to use this desk.")
    return user


def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access is required.")
    return user
