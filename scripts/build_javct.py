import csv
import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# =========================
# CONFIGURATION
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_CSV = BASE_DIR / "results/processed/javct.csv"
CODES_TXT = BASE_DIR / "docs/codes.txt"

OUTPUT_JSON = BASE_DIR / "docs/javct.json"
OUTPUT_HTML = BASE_DIR / "docs/javct.html"

def load_guru_codes() -> set[str]:
    """Load JAV.guru codes (lowercased) from codes.txt."""
    if not CODES_TXT.exists():
        return set()
    return {
        line.strip().lower()
        for line in CODES_TXT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def clean_code(c: str) -> str:
    cleaned = re.sub(r"-(rm|sub|c|uncensored|leak|hd)$", "", c.strip().lower())
    return cleaned


def normalize_code(c: str) -> str:
    return "".join(ch for ch in c if ch.isalnum())


def generate():

    if not INPUT_CSV.exists():
        print(f"[x] CSV not found: {INPUT_CSV}")
        return

    guru_codes = load_guru_codes()
    guru_codes_norm = {normalize_code(c) for c in guru_codes}
    print(f"[i] Loaded {len(guru_codes)} codes from codes.txt")

    data = []
    seen_codes = set()

    with INPUT_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for r in reader:
            code = (r.get("code") or "").strip()
            if not code:
                continue

            code_lower = code.lower()
            if code_lower in seen_codes:
                continue
            seen_codes.add(code_lower)

            cleaned = clean_code(code_lower)
            is_guru = (
                code_lower in guru_codes
                or cleaned in guru_codes
                or normalize_code(cleaned) in guru_codes_norm
            )
            source_tag = "jav.guru" if is_guru else "new"

            data.append({
                "code": code,
                "title": (r.get("title") or "").strip(),
                "image_url": (r.get("image_url") or "").strip(),
                "page_url": (r.get("page_url") or "").strip(),
                "views": (r.get("views") or "").strip(),
                "date_scraped": (r.get("date_scraped") or "").strip(),
                "source_tag": source_tag,
            })

    guru_count = sum(1 for d in data if d["source_tag"] == "jav.guru")
    new_count = len(data) - guru_count

    print(f"[i] Tagged: {guru_count} JAV.guru, {new_count} New")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    env = Environment(loader=FileSystemLoader(BASE_DIR / "templates"))
    template = env.get_template("javct.html")
    html = template.render(current_page="javct")
    OUTPUT_HTML.write_text(html, encoding="utf-8")

    print("[ok] JavCT page build generated.")
    print(f"Videos: {len(data)}")

if __name__ == "__main__":
    generate()
