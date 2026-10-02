"""[Dev 2] Auth routes. Login/logout/me are REAL from Phase 0; invite accept is a stub for Dev 2."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth import (clear_session, current_user, issue_session, public, user_out, verify_password)
from ..contracts import InviteAcceptRequest, LoginRequest, OkResponse, UserOut
from ..db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", dependencies=[Depends(public)], response_model=UserOut)
def login(body: LoginRequest, response: Response, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute("SELECT * FROM users WHERE email = ?", (body.email.strip(),)).fetchone()
    if row is None or not verify_password(row["password_hash"], body.password):
        raise HTTPException(401, "Invalid email or password")
    issue_session(response, row["id"], row["role"])
    return user_out(row)


@router.post("/logout", dependencies=[Depends(public)], response_model=OkResponse)
def logout(response: Response):
    clear_session(response)
    return OkResponse()


@router.get("/me", dependencies=[Depends(public)], response_model=UserOut)
def me(user=Depends(current_user)):
    return user_out(user)


@router.post("/invite/{code}/accept", dependencies=[Depends(public)], response_model=UserOut)
def accept_invite(code: str, body: InviteAcceptRequest):
    raise HTTPException(501, "stub: Dev 2 implements invite acceptance")
