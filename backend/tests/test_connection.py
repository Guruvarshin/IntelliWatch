import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(dotenv_path="../.env")

client = MongoClient(os.environ["MONGODB_URI"])
db = client.get_default_database()

result = db.connection_test.insert_one({"hello": "intelliwatch"})
print("Inserted document ID:", result.inserted_id)

doc = db.connection_test.find_one({"_id": result.inserted_id})
print("Read back:", doc)

db.connection_test.delete_one({"_id": result.inserted_id})
print("Cleaned up test document. Connection works.")
