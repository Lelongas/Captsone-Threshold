# main_mongo.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from app.db_mongo import get_db, ensure_indexes
from app.services.recipe_service_mongo import get_matching_recipes_mongo, get_recipe_by_id_mongo

app = FastAPI(title="Fridge → Recipes API (MongoDB Atlas)", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def _startup():
    ensure_indexes(get_db())

class RecipeQuery(BaseModel):
    ingredients: List[str]
    tags: Optional[List[str]] = []

@app.get("/health")
def health():
    try:
        db = get_db()
        db.command("ping")
        return {"status": "ok", "db": "reachable"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)}

@app.post("/recipes")
def recipes(q: RecipeQuery):
    return {"results": get_matching_recipes_mongo(q.ingredients, q.tags or [], limit=10)}

@app.get("/recipes/{rid}")
def recipe_detail(rid: str):
    data = get_recipe_by_id_mongo(rid)
    if not data:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return data
