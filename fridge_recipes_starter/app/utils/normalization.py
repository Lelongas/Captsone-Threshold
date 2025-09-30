import re
def normalize_token(s: str) -> str:
    if not s: return ""
    t = re.sub(r"[^a-z0-9\s\-]", "", str(s).lower()).strip()
    t = re.sub(r"\s+", " ", t)
    return t
