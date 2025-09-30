# etl/load_recipes_mongo.py
import json, re, ast, pandas as pd
from dotenv import load_dotenv; load_dotenv()
from app.db_mongo import get_db, ensure_indexes
from app.utils.normalization import normalize_token

def parse_list_cell(val):
    if val is None: return []
    if isinstance(val, list): return [str(x) for x in val]
    s = str(val).strip()
    if not s: return []
    if s.startswith("[") and s.endswith("]"):
        for parser in (json.loads, ast.literal_eval):
            try:
                arr = parser(s)
                if isinstance(arr, list): return [str(x) for x in arr]
            except Exception:
                pass
    return [p.strip() for p in re.split(r"[;,]", s) if p.strip()]

def parse_steps_cell(val):
    if val is None: return []
    if isinstance(val, list): return [clean_display(x) for x in val if str(x).strip()]
    s = str(val).strip()
    if not s: return []
    if s.startswith("[") and s.endswith("]"):
        for parser in (json.loads, ast.literal_eval):
            try:
                arr = parser(s)
                if isinstance(arr, list):
                    return [clean_display(x) for x in arr if str(x).strip()]
            except Exception:
                pass
    lines = [l.strip() for l in re.split(r"\r?\n+", s) if l.strip()]
    if len(lines) > 1:
        return [re.sub(r"^\s*(\d+[\)\.\:\-]\s*|[-•]\s*)", "", l) for l in lines]
    parts = [p.strip() for p in re.split(r"\s*[;|]\s*", s) if p.strip()]
    if len(parts) > 1:
        return [re.sub(r"^\s*(\d+[\)\.\:\-]\s*|[-•]\s*)", "", p) for p in parts]
    return [s]

def clean_display(text: str) -> str:
    t = str(text).strip().strip("[]\"'")
    return re.sub(r"\s+", " ", t)

def parse_prep_time(val):
    """Return minutes as int, or None. Handles: 55, 'minutes 55', '55 minutes', '1 hr 30 min', 'PT45M', '1:30'."""
    if val is None:
        return None
    if isinstance(val, (int, float)) and not pd.isna(val):
        return int(val)

    s = str(val).strip().lower()
    if not s:
        return None

    m = re.match(r"^pt(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$", s)
    if m:
        h = int(m.group(1) or 0)
        mi = int(m.group(2) or 0)
        sec = int(m.group(3) or 0)
        return h * 60 + mi + (1 if (h == 0 and mi == 0 and sec > 0) else 0)

    hours = re.search(r"(\d+)\s*(h|hr|hour|hours)", s)
    mins  = re.search(r"(\d+)\s*(m|min|mins|minute|minutes)", s)
    total = 0
    if hours: total += int(hours.group(1)) * 60
    if mins:  total += int(mins.group(1))
    if total > 0: return total

    m = re.match(r"^\s*(\d+)\s*:\s*(\d{1,2})\s*$", s)
    if m: return int(m.group(1)) * 60 + int(m.group(2))

    nums = re.findall(r"\d+", s)  # covers 'minutes 55'
    return int(nums[-1]) if nums else None

def detect_columns(df: pd.DataFrame):
    cols = {c.lower().strip(): c for c in df.columns}
    def col_like(*names):
        for n in names:
            if n in cols: return cols[n]
        for k, orig in cols.items():
            for n in names:
                if n in k: return orig
        return None
    return dict(
        id=col_like("id","external_id","recipe_id"),
        title=col_like("title","name"),
        desc=col_like("description","desc","summary"),
        # intentionally ignoring image/cuisine/source
        prep=col_like("prep_time_min","prep","time","cook_time","total_time","ready in","time to make","duration","minutes"),
        ingredients=col_like("ingredients","ingredient_list","ings"),
        tags=col_like("tags","labels","categories"),
        steps=col_like("steps","instructions","directions","method","procedure"),
    )

def load_excel_to_mongo(xlsx_path: str, drop_existing: bool = True):
    db = get_db()
    if drop_existing:
        db.recipes.drop()  # keep bookmarks intact

    df = pd.read_excel(xlsx_path)
    cols = detect_columns(df)

    docs = []
    recipes_inserted = ing_links = tag_links = 0

    for i, row in df.iterrows():
        title = clean_display(row[cols["title"]]) if cols["title"] else f"Recipe {i+1}"
        desc  = clean_display(row[cols["desc"]])  if cols["desc"]  and pd.notna(row[cols["desc"]])  else None

        prep_time = parse_prep_time(row[cols["prep"]]) if cols["prep"] and pd.notna(row[cols["prep"]]) else None
        external_id = clean_display(row[cols["id"]]) if cols["id"] and pd.notna(row[cols["id"]]) else None

        ing_raw = parse_list_cell(row[cols["ingredients"]]) if cols["ingredients"] else []
        tag_raw = parse_list_cell(row[cols["tags"]])        if cols["tags"]        else []
        steps_raw = parse_steps_cell(row[cols["steps"]])    if cols["steps"] and pd.notna(row[cols["steps"]]) else []

        ingredients = [{"display": clean_display(x), "normalized": normalize_token(x)} for x in ing_raw]
        tags = [{"name": clean_display(x), "normalized": normalize_token(x)} for x in tag_raw]

        norm_ings = sorted({i["normalized"] for i in ingredients if i["normalized"]})
        norm_tags = sorted({t["normalized"] for t in tags if t["normalized"]})

        docs.append({
            "external_id": external_id,
            "title": title,
            "description": desc,
            "prep_time_min": prep_time,
            "ingredients": ingredients,
            "tags": tags,
            "steps": steps_raw,
            "normalized_ingredients": norm_ings,
            "normalized_tags": norm_tags,
        })
        recipes_inserted += 1
        ing_links += len(norm_ings)
        tag_links += len(norm_tags)

    if docs:
        db.recipes.insert_many(docs, ordered=False)

    ensure_indexes(db)
    return {
        "recipes_inserted": recipes_inserted,
        "links_recipe_ingredients": ing_links,
        "links_recipe_tags": tag_links
    }

if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "test.xlsx"
    print(load_excel_to_mongo(p))
