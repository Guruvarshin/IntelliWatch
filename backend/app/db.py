import os

from motor.motor_asyncio import AsyncIOMotorClient

mongo_client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
db = mongo_client.get_default_database()
