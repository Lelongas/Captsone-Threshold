# app/db_mongo.py
import os
from pymongo import MongoClient, ASCENDING

def get_db():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    name = os.getenv("MONGODB_DB", "fridge_recipes")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[name]

def ensure_indexes(db):
    # Core indexes for fast matching and filtering
    db.recipes.create_index([("normalized_ingredients", ASCENDING)])
    db.recipes.create_index([("normalized_tags", ASCENDING)])
    # Optional text index for search across fields
    db.recipes.create_index([("title", "text"), ("description", "text"), ("steps", "text")])

    # Prevent duplicate bookmarks per owner (if/when you add bookmarks)
    db.bookmarks.create_index(
        [("user_id", ASCENDING), ("device_key", ASCENDING), ("recipe_id", ASCENDING)],
        unique=True
    )
