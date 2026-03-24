from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.core.security import user_id_from_auth_header


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    user_id = user_id_from_auth_header(authorization)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user
