# app/services/recipe_service.py
from typing import List, Dict, Any

from sqlalchemy import select, func, literal_column

from app.database import SessionLocal
from app.models import Recipe, Ingredient, RecipeIngredient, Tag, RecipeTag


def get_matching_recipes(
    ingredients: List[str],
    tags: List[str] | None = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns recipes scored by overlap with provided *normalized* ingredient names.
    """
    if tags is None:
        tags = []

    norm_ings = [i.lower().strip() for i in ingredients if i and i.strip()]
    if not norm_ings:
        return []

    with SessionLocal() as db:
        # Resolve ingredient ids for normalized names
        ing_ids = db.execute(
            select(Ingredient.id).where(Ingredient.normalized_name.in_(norm_ings))
        ).scalars().all()
        if not ing_ids:
            return []

        # Matches per recipe
        sub_hits = (
            select(RecipeIngredient.recipe_id, func.count().label("hit_count"))
            .where(RecipeIngredient.ingredient_id.in_(ing_ids))
            .group_by(RecipeIngredient.recipe_id)
            .subquery()
        )

        # Total ingredients per recipe
        sub_total = (
            select(RecipeIngredient.recipe_id, func.count().label("total_count"))
            .group_by(RecipeIngredient.recipe_id)
            .subquery()
        )

        q = (
            select(
                Recipe.id,
                Recipe.title,
                Recipe.image_url,
                Recipe.prep_time_min,
                Recipe.cuisine,
                sub_hits.c.hit_count.label("hit_count"),
                ((sub_hits.c.hit_count * 1.0) / (sub_total.c.total_count + 0.0)).label("match_pct"),
            )
            .join(sub_hits, Recipe.id == sub_hits.c.recipe_id)
            .join(sub_total, Recipe.id == sub_total.c.recipe_id)
        )

        if tags:
            tnorm = [t.lower().strip() for t in tags if t and t.strip()]
            q = (
                q.join(RecipeTag, RecipeTag.recipe_id == Recipe.id)
                 .join(Tag, Tag.id == RecipeTag.tag_id)
                 .where(Tag.normalized_name.in_(tnorm))
                 .group_by(
                     Recipe.id, Recipe.title, Recipe.image_url, Recipe.prep_time_min,
                     Recipe.cuisine, sub_hits.c.hit_count, sub_total.c.total_count
                 )
            )

        # Order by labeled columns (SQLite-safe)
        q = q.order_by(
            literal_column("match_pct").desc(),
            literal_column("hit_count").desc(),
        ).limit(limit)

        rows = db.execute(q).all()

        out: List[Dict[str, Any]] = []
        seen: set[int] = set()
        for rid, title, image_url, prep, cuisine, hits, pct in rows:
            if rid in seen:
                continue
            seen.add(rid)
            out.append({
                "recipe_id": rid,
                "title": title,
                "image_url": image_url,
                "prep_time_min": prep,
                "cuisine": cuisine,
                "match_count": int(hits or 0),
                "match_pct": float(pct or 0.0),
            })
        return out


def get_recipe_by_id(recipe_id: int) -> Dict[str, Any] | None:
    with SessionLocal() as db:
        r = db.get(Recipe, recipe_id)
        if not r:
            return None

        ings = db.execute(
            select(Ingredient.name, Ingredient.normalized_name)
            .join(RecipeIngredient, RecipeIngredient.ingredient_id == Ingredient.id)
            .where(RecipeIngredient.recipe_id == recipe_id)
        ).all()

        tags = db.execute(
            select(Tag.name, Tag.type)
            .join(RecipeTag, RecipeTag.tag_id == Tag.id)
            .where(RecipeTag.recipe_id == recipe_id)
        ).all()

        return {
            "recipe_id": r.id,
            "title": r.title,
            "description": r.description,
            "image_url": r.image_url,
            "prep_time_min": r.prep_time_min,
            "cuisine": r.cuisine,
            "source_url": r.source_url,
            "ingredients": [{"name": n, "normalized": nn} for (n, nn) in ings],
            "tags": [{"name": n, "type": t} for (n, t) in tags],
        }
