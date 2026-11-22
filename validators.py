"""Input rules shared by the menu, the CSV importer and the tests. Each parser raises ValueError."""
import re
from collections import namedtuple
from datetime import date, datetime

from .config import CATEGORIES

Field = namedtuple("Field", "key label parse")


def title(s):
    s = s.strip()
    if not 3 <= len(s) <= 80:
        raise ValueError("Title must be 3-80 characters.")
    return s


def category(s):
    s = s.strip()
    if s.isdigit() and 1 <= int(s) <= len(CATEGORIES):
        return CATEGORIES[int(s) - 1]
    for c in CATEGORIES:
        if c.lower() == s.lower():
            return c
    raise ValueError("Pick a category by number or exact name.")


def severity(s):
    try:
        n = int(str(s).strip())
    except ValueError:
        raise ValueError("Severity must be a whole number 1-5.")
    if not 1 <= n <= 5:
        raise ValueError("Severity must be between 1 and 5.")
    return n


def keywords(s):
    parts = [p.strip().lower() for p in re.split(r"[,;]", s) if p.strip()]
    if not parts:
        raise ValueError("Enter at least one keyword (comma separated).")
    if any(len(p) > 30 for p in parts):
        raise ValueError("Each keyword must be 30 characters or fewer.")
    return parts


def steps(s):
    s = s.strip()
    if not 10 <= len(s) <= 800:
        raise ValueError("Steps must be 10-800 characters (separate steps with ' | ').")
    return s


def yes_no(s):
    s = str(s).strip().lower()
    if s in ("y", "yes", "true", "1"):
        return True
    if s in ("n", "no", "false", "0"):
        return False
    raise ValueError("Answer yes or no.")


def review_date(s):
    try:
        d = datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must look like YYYY-MM-DD.")
    if d > date.today():
        raise ValueError("Date cannot be in the future.")
    return d.isoformat()


FIELDS = [
    Field("title", "Title", title),
    Field("category", "Category (number or name)", category),
    Field("severity", "Severity 1 (minor) - 5 (life-threatening)", severity),
    Field("keywords", "Keywords (comma separated)", keywords),
    Field("steps", "Steps (separate with ' | ')", steps),
    Field("call_emergency", "Call emergency services? (y/n)", yes_no),
    Field("last_reviewed", "Last reviewed YYYY-MM-DD (Enter = today)", review_date),
]


def validate_row(row):
    """Validate a dict of raw strings. Returns (clean_dict, list_of_errors)."""
    clean, errors = {}, []
    for f in FIELDS:
        try:
            clean[f.key] = f.parse(str(row.get(f.key, "") or ""))
        except ValueError as e:
            errors.append(f"{f.key}: {e}")
    return clean, errors
