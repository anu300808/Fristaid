# First-Aid Information Finder

A menu-driven Python app to search a local file of basic first-aid topics. Educational only: in an emergency call your local emergency number.

## Run
    python firstaid.py            # Python 3.10+
    pip install matplotlib        # optional, for charts
    python -m unittest -v         # 33 automated tests

## Design (layers, each in its own module of `firstaid_app/`)
| Module | Role |
|---|---|
| `models.py` | `Entry` dataclass (one record) |
| `validators.py` | input rules; same rules for the menu and CSV import |
| `repository.py` | `EntryRepository` interface + `JsonEntryRepository` (atomic save, corrupt-file backup) |
| `services.py` | ranked typo-tolerant search, pluggable warning rules, summary statistics |
| `reports.py` | exporter classes (Markdown, text, CSV) and Matplotlib charts |
| `importer.py` | bulk CSV import with row-by-row error log |
| `ui.py` / `cli.py` | terminal output and the menu controller |

## Features
Search (typo-tolerant, ranked, category and severity filters), browse, add, delete, emergency quick list, executive summary, threshold warnings, charts, MD/TXT/CSV export, bulk CSV import. Data is kept in `firstaid_data.json`; set `FIRSTAID_DATA` to use another file.
