from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.recipe_service import get_matching_recipes, get_recipe_by_id
app = FastAPI(title="Fridge → Recipes API", version="0.1.0")
class RecipeQuery(BaseModel):
    ingredients: List[str]
    tags: Optional[List[str]] = []
@app.get("/health")
def health(): return {"status": "ok"}
@app.post("/recipes")
def recipes(q: RecipeQuery):
    data = get_matching_recipes(q.ingredients, q.tags or [], limit=10)
    return {"results": data}
@app.get("/recipes/{rid}")
def recipe_detail(rid: int):
    data = get_recipe_by_id(rid)
    if not data:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return data
