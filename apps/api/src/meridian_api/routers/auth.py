from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from meridian_db.models import User
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from meridian_api.deps import COOKIE, current_user, db_session
from meridian_api.passwords import verify_password
from meridian_api.session_token import issue_token

router = APIRouter(prefix="/api/v1/auth")


class LoginBody(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=200)


@router.post("/login")
def login(body: LoginBody, response: Response, db: Session = Depends(db_session)) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    response.set_cookie(
        COOKIE,
        issue_token(str(user.id)),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
        max_age=7 * 24 * 3600,
    )
    return {"email": user.email, "displayName": user.display_name, "role": user.role}


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie(COOKIE, path="/")
    return {"status": "signed-out"}


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict[str, str]:
    return {"email": user.email, "displayName": user.display_name, "role": user.role}
