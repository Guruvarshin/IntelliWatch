from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI

from app.auth import get_current_user
from app.db import db
from app.routers import competitors, internal, settings

app = FastAPI(title="IntelliWatch API")
app.include_router(competitors.router)
app.include_router(internal.router)
app.include_router(settings.router)


@app.get("/health")
async def health():
    await db.command("ping")
    return {"status": "ok", "database": db.name}


@app.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user
