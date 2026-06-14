import os

import jwt
from fastapi import Header, HTTPException


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ")

    try:
        payload = jwt.decode(
            token,
            os.environ["AUTH_SECRET"],
            algorithms=["HS256"],
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {"user_id": payload["sub"], "email": payload.get("email")}
