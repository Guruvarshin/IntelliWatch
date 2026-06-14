from bson import ObjectId

from app.crypto import decrypt


async def get_user_api_keys(db, user_id: str) -> dict:
    """Fetches and decrypts the given user's BYOK API keys. Returns
    {"openai_api_key": str | None, "anthropic_api_key": str | None} --
    None for any key the user hasn't configured, so callers can pass these
    straight into GraphState and let the LLM clients fall back to env vars."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    openai_key = user.get("openai_api_key_encrypted") if user else None
    anthropic_key = user.get("anthropic_api_key_encrypted") if user else None

    return {
        "openai_api_key": decrypt(openai_key) if openai_key else None,
        "anthropic_api_key": decrypt(anthropic_key) if anthropic_key else None,
    }
