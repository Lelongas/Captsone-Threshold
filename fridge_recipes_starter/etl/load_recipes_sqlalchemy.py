import json, re, ast, pandas as pd
from sqlalchemy import select, func
from app.database import engine, SessionLocal
from app.models import Base, Recipe, Ingredient, RecipeIngredient, Tag, RecipeTag
from app.utils.normalization import normalize_token
def parse_list_cell(val):
    """
    Robustly parse cells that may contain:
      - JSON arrays: ["a","b"]
      - Python repr arrays: ['a','b']
      - Comma/semicolon separated strings: a,b ; c
    Returns a list[str].
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val]

    s = str(val).strip()
    if not s:
        return []

    # Try JSON first
    if s.startswith("[") and s.endswith("]"):
        try:
            arr = json.loads(s)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except Exception:
            pass
        # Try Python literal list e.g. "['a','b']"
        try:
            arr = ast.literal_eval(s)
            if isinstance(arr, list):
                return [str(x) for x in arr]
        except Exception:
            pass

    # Fallback: split on comma/semicolon
    parts = re.split(r"[;,]", s)
    return [p.strip() for p in parts if p.strip()]


def clean_display(text: str) -> str:
    """
    Tidy up display text:
      - trim whitespace
      - strip leading/trailing quotes/brackets
      - collapse multiple spaces
    """
    t = str(text).strip()
    t = t.strip("[]\"'")
    t = re.sub(r"\s+", " ", t)
    return t


def detect_columns(df: pd.DataFrame):
    cols = {c.lower().strip(): c for c in df.columns}

    def col_like(*names):
        for n in names:
            if n in cols:
                return cols[n]
        for k, orig in cols.items():
            for n in names:
                if n in k:
                    return orig
        return None

    return dict(
        id=col_like("id", "external_id", "recipe_id"),
        title=col_like("title", "name"),
        desc=col_like("description", "desc", "summary"),
        img=col_like("image_url", "image", "photo"),
        prep=col_like("prep_time_min", "prep", "time", "cook_time", "total_time"),
        cuisine=col_like("cuisine", "category"),
        src=col_like("source_url", "url", "link"),
        ingredients=col_like("ingredients", "ingredient_list", "ings"),
        tags=col_like("tags", "labels", "categories"),
    )


def upsert_ingredient(session, display: str):
    norm = normalize_token(display)
    if not norm:
        return None
    row = session.execute(
        select(Ingredient).where(Ingredient.normalized_name == norm)
    ).scalar_one_or_none()
    if row:
        return row
    row = Ingredient(name=display.strip(), normalized_name=norm)
    session.add(row)
    session.flush()
    return row


def upsert_tag(session, display: str, ttype: str = ""):
    norm = normalize_token(display)
    if not norm:
        return None
    row = session.execute(
        select(Tag).where(Tag.normalized_name == norm, Tag.type == (ttype or None))
    ).scalar_one_or_none()
    if row:
        return row
    row = Tag(name=display.strip(), normalized_name=norm, type=ttype or None)
    session.add(row)
    session.flush()
    return row


def load_excel(path: str):
    # Dev-friendly: recreate schema each run
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    df = pd.read_excel(path)
    cols = detect_columns(df)

    recipes_inserted = 0
    links_ing = 0
    links_tag = 0

    with SessionLocal() as session:
        for i, row in df.iterrows():
            title = str(row[cols["title"]]).strip() if cols["title"] else f"Recipe {i+1}"
            title = clean_display(title)

            desc = (
                clean_display(row[cols["desc"]])
                if cols["desc"] and pd.notna(row[cols["desc"]])
                else None
            )
            image_url = (
                clean_display(row[cols["img"]])
                if cols["img"] and pd.notna(row[cols["img"]])
                else None
            )
            cuisine = (
                clean_display(row[cols["cuisine"]])
                if cols["cuisine"] and pd.notna(row[cols["cuisine"]])
                else None
            )
            source_url = (
                clean_display(row[cols["src"]])
                if cols["src"] and pd.notna(row[cols["src"]])
                else None
            )

            prep_time_val = None
            if cols["prep"] and pd.notna(row[cols["prep"]]):
                try:
                    prep_time_val = int(row[cols["prep"]])
                except Exception:
                    m = re.search(r"\d+", str(row[cols["prep"]]))
                    prep_time_val = int(m.group(0)) if m else None

            external_id = None
            if cols["id"] and pd.notna(row[cols["id"]]):
                external_id = clean_display(row[cols["id"]])

            recipe = Recipe(
                external_id=external_id,
                title=title,
                description=desc,
                image_url=image_url,
                prep_time_min=prep_time_val,
                cuisine=cuisine,
                source_url=source_url,
            )
            session.add(recipe)
            session.flush()
            recipes_inserted += 1

            # Ingredients
            ing_list = parse_list_cell(row[cols["ingredients"]]) if cols["ingredients"] else []
            seen_ing_ids = set()
            for ing in ing_list:
                disp = clean_display(ing)
                ing_row = upsert_ingredient(session, disp)
                if ing_row and ing_row.id not in seen_ing_ids:
                    session.add(
                        RecipeIngredient(
                            recipe_id=recipe.id,
                            ingredient_id=ing_row.id,
                            raw_text=disp,
                        )
                    )
                    links_ing += 1
                    seen_ing_ids.add(ing_row.id)

            # Tags
            tag_list = parse_list_cell(row[cols["tags"]]) if cols["tags"] else []
            seen_tag_ids = set()
            for tag in tag_list:
                disp_tag = clean_display(tag)
                tag_row = upsert_tag(session, disp_tag, ttype="")
                if tag_row and tag_row.id not in seen_tag_ids:
                    session.add(RecipeTag(recipe_id=recipe.id, tag_id=tag_row.id))
                    links_tag += 1
                    seen_tag_ids.add(tag_row.id)

        # Commit & gather counts while session is open
        session.commit()

        ing_count = session.execute(
            select(func.count()).select_from(Ingredient)
        ).scalar_one()
        tag_count = session.execute(
            select(func.count()).select_from(Tag)  # unique tags
        ).scalar_one()

    return {
        "recipes_inserted": recipes_inserted,
        "ingredient_rows": ing_count,
        "tag_rows": tag_count,
        "links_recipe_ingredients": links_ing,
        "links_recipe_tags": links_tag,
    }


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "test.xlsx"
    print(load_excel(p))