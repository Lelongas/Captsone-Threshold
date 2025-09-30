# app/services/recipe_service_mongo.py
from typing import List, Dict, Any
from bson import ObjectId
from app.db_mongo import get_db

def get_matching_recipes_mongo(ingredients: List[str], tags: List[str] | None = None, limit: int = 10) -> List[Dict[str, Any]]:
    tags = tags or []
    norm_ings = sorted({(i or "").strip().lower() for i in ingredients if i and i.strip()})
    norm_tags = sorted({(t or "").strip().lower() for t in tags if t and t.strip()})
    if not norm_ings:
        return []

    db = get_db()
    pipeline = [
        {"$match": {"normalized_ingredients": {"$in": list(norm_ings)}}},
        *([{"$match": {"normalized_tags": {"$all": list(norm_tags)}}}] if norm_tags else []),
        {"$addFields": {
            "match_count": {"$size": {"$setIntersection": ["$normalized_ingredients", list(norm_ings)]}},
            "total_count": {"$size": "$normalized_ingredients"},
        }},
        {"$addFields": {
            "match_pct": {"$cond": [{"$gt": ["$total_count", 0]}, {"$divide": ["$match_count", "$total_count"]}, 0]}
        }},
        {"$sort": {"match_pct": -1, "match_count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 1, "title": 1, "prep_time_min": 1, "match_count": 1, "match_pct": 1}},
    ]
    rows = list(db.recipes.aggregate(pipeline))
    return [{
        "recipe_id": str(r["_id"]),
        "title": r.get("title"),
        "prep_time_min": r.get("prep_time_min"),
        "match_count": int(r.get("match_count", 0)),
        "match_pct": float(r.get("match_pct", 0.0)),
    } for r in rows]

def get_recipe_by_id_mongo(recipe_id: str) -> Dict[str, Any] | None:
    db = get_db()
    try:
        doc = db.recipes.find_one({"_id": ObjectId(recipe_id)})
    except Exception:
        return None
    if not doc:
        return None
    return {
        "recipe_id": str(doc["_id"]),
        "title": doc.get("title"),
        "description": doc.get("description"),
        "prep_time_min": doc.get("prep_time_min"),
        "ingredients": doc.get("ingredients", []),
        "tags": doc.get("tags", []),
        "steps": doc.get("steps", []),
    }
