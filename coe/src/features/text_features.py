"""Multilingual operator-note normalisation (English / Tanglish / Tamil script).

Two complementary mechanisms are used so the system does not depend on a hand-built dictionary alone:
  1. concept tokens (CT_*) appended from a small, auditable regex lexicon -> shop-floor vocabulary maps to the same
     token regardless of language;
  2. character n-gram TF-IDF (in feature_engineering) which handles typos, Tamil script and unseen spellings.
The lexicon is deliberately short so a supervisor / native speaker can review it in minutes.
"""
import re
import unicodedata

CONCEPTS = [
    ("CT_ALIGN", r"align|sariyaa|seating|reposition|shift aay|maathi vek|அமர|இடம் மாற"),
    ("CT_SENSOR", r"sensor|photoeye|proximity|lens|dust|சென்சார்|தூசி"),
    ("CT_BLOCKED", r"block|degrad|false trigger|அடைப்பு|தடை"),
    ("CT_OPERATOR", r"operator|ஆபரேட்டர்|manual load"),
    ("CT_DELAY", r"late|delay|lag|wait|edukka|pannitu irundh|தாமத|காத்திரு"),
    ("CT_SAFETY", r"safety|curtain|zone|perimeter|breach|பாதுகாப்பு|மண்டல"),
    ("CT_ROBOT", r"robot|cobot|gripper|joint|torque|axis|ரோபோ"),
    ("CT_RESET", r"reset|restart|recover|hang aay|மீட்டமை"),
    ("CT_TOOL", r"tool|end effector|jaw|swapper|கருவி"),
    ("CT_QUALITY", r"quality|inspect|gauge|dimension|measure|தரம்|சரிபார்"),
    ("CT_STOCK", r"stock|feeder|bin|trolley|agv|material shortage|depleted|illa|இல்லை|பொருள் இல்லை"),
    ("CT_GENERIC", r"^(ok now|checked|small stop|restarted|cleared|nothing found|resume|reset done|seri aay|சரி ஆனது)"),
]
_COMPILED = [(name, re.compile(p)) for name, p in CONCEPTS]
_TANGLISH = re.compile(r"aagala|aachu|aayiduchu|panninom|pannitu|pannadhum|irundh|sariyaa|konjam|illa|edukka|maathi|vekkanum|seri aay|irundhom|panni")
_TAMIL = re.compile(r"[\u0B80-\u0BFF]")


def clean_note(note) -> str:
    if note is None or (isinstance(note, float) and note != note):
        return ""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(note)).strip().lower())


def detect_language(note) -> str:
    """'none' | 'ta' (Tamil script) | 'tanglish' | 'en'."""
    n = clean_note(note)
    if not n:
        return "none"
    if _TAMIL.search(n):
        return "ta"
    if _TANGLISH.search(n):
        return "tanglish"
    return "en"


def normalise_note(note) -> str:
    """Return cleaned note followed by canonical concept tokens found in it."""
    n = clean_note(note)
    if not n:
        return "CT_EMPTY"
    tokens = [name for name, rx in _COMPILED if rx.search(n)]
    return n + " " + " ".join(tokens)
