import re, unicodedata
STOP = {"fresh","chopped","diced","minced","large","small","cup","cups","tbsp","tsp"}
PUNCT = re.compile(r"[^\w\s]")
def nfkc(s: str) -> str: return unicodedata.normalize("NFKC", s)
def normalize_token(raw: str) -> str:
    s = nfkc(str(raw)).lower().strip()
    s = PUNCT.sub(" ", s)
    toks = [t for t in s.split() if t and t not in STOP]
    if not toks: return ""
    head = toks[0]
    if len(head) > 4:
        if head.endswith("es"): head = head[:-2]
        elif head.endswith("s"): head = head[:-1]
    return " ".join([head] + toks[1:]).strip()
