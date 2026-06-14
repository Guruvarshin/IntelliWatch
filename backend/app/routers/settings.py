from bson import ObjectId
from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.crypto import encrypt
from app.db import db
from app.models import ApiKeysIn

router = APIRouter(prefix="/me", tags=["settings"])


@router.get("/api-keys")
async def get_api_keys(current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"_id": ObjectId(current_user["user_id"])})
    return {
        "openai_api_key_set": bool(user and user.get("openai_api_key_encrypted")),
        "anthropic_api_key_set": bool(user and user.get("anthropic_api_key_encrypted")),
    }


@router.put("/api-keys")
async def set_api_keys(
    body: ApiKeysIn, current_user: dict = Depends(get_current_user)
):
    updates = body.model_dump(exclude_unset=True)

    set_fields = {}
    unset_fields = {}
    for field, db_field in [
        ("openai_api_key", "openai_api_key_encrypted"),
        ("anthropic_api_key", "anthropic_api_key_encrypted"),
    ]:
        if field not in updates:
            continue
        value = updates[field]
        if value == "":
            unset_fields[db_field] = ""
        else:
            set_fields[db_field] = encrypt(value)

    update_doc = {}
    if set_fields:
        update_doc["$set"] = set_fields
    if unset_fields:
        update_doc["$unset"] = unset_fields

    if update_doc:
        await db.users.update_one(
            {"_id": ObjectId(current_user["user_id"])}, update_doc
        )

    return await get_api_keys(current_user)
