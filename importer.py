import csv
from dataclasses import dataclass
from datetime import date, datetime

from .validators import FIELDS, validate_row

REQUIRED = {f.key for f in FIELDS if f.key != "last_reviewed"}


@dataclass
class ImportResult:
    added: int
    errors: list


class CsvImporter:
    def __init__(self, repo):
        self._repo = repo

    def run(self, path):
        """Import valid rows, collect row-by-row errors. Raises OSError / ValueError for unusable files."""
        existing = {e.title.lower() for e in self._repo.list_all()}
        added, errors = 0, []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            cols = {c.strip() for c in (reader.fieldnames or [])}
            if not REQUIRED.issubset(cols):
                raise ValueError("Missing required columns: " + ", ".join(sorted(REQUIRED - cols)))
            for line_no, row in enumerate(reader, start=2):
                row = {(k or "").strip(): v for k, v in row.items()}
                if not (row.get("last_reviewed") or "").strip():
                    row["last_reviewed"] = date.today().isoformat()
                clean, errs = validate_row(row)
                if not errs and clean["title"].lower() in existing:
                    errs.append("title: duplicate of an existing entry")
                if errs:
                    errors.append(f"Row {line_no}: " + "; ".join(errs))
                    continue
                self._repo.add(clean)
                existing.add(clean["title"].lower())
                added += 1
        return ImportResult(added, errors)


def write_error_log(path, source, result):
    with open(path, "w", encoding="utf-8") as lf:
        lf.write(f"Import of {source} at {datetime.now():%Y-%m-%d %H:%M}\nImported: {result.added}  Rejected: {len(result.errors)}\n\n")
        lf.write("\n".join(result.errors) or "No errors.")
