"""Menu controller: reads input, calls services, prints with ui."""
from datetime import date

from . import ui, validators as V
from .config import CATEGORIES, DATA_FILE, ERROR_LOG, PAGE_SIZE, REPORT_DIR
from .importer import CsvImporter, write_error_log
from .repository import JsonEntryRepository
from .reports import export_all, make_chart, summary_text
from .services import SearchService, SummaryService, WarningService
from .ui import CYAN, DIM, GREEN, RED, RESET, YELLOW, BOLD

MENU = f"""
{BOLD}MAIN MENU{RESET}
  1. Search first-aid topics (typo-tolerant, ranked)
  2. Browse all topics
  3. Add a new entry
  4. Delete an entry
  5. Executive summary
  6. Threshold warnings
  7. Generate charts (Matplotlib)
  8. Export reports (MD / TXT / CSV + chart)
  9. Bulk import from CSV
 10. Emergency quick list
  0. Exit
"""


class App:
    def __init__(self, repo, search, warnings, summary):
        self.repo, self.search, self.warnings, self.summary = repo, search, warnings, summary
        self.actions = {"1": self.search_screen, "2": self.browse, "3": self.add_entry, "4": self.delete_entry,
                        "5": self.show_summary, "6": self.show_warnings, "7": self.chart, "8": self.export,
                        "9": self.import_csv, "10": self.emergency}

    def ask(self, prompt, parse=None, default=None):
        """Loop until the parser accepts the input."""
        while True:
            try:
                raw = input(f"{CYAN}{prompt}{RESET}: ")
            except (EOFError, KeyboardInterrupt):
                print()
                raise SystemExit(0)
            if not raw.strip() and default is not None:
                raw = default
            if parse is None:
                return raw.strip()
            try:
                return parse(raw)
            except ValueError as e:
                print(f"  {RED}x {e}{RESET}")

    def show_categories(self):
        print("\nCategories:")
        for i, c in enumerate(CATEGORIES, 1):
            print(f"  {i:>2}. {c}")

    def pick_category(self):
        self.show_categories()
        raw = self.ask("Category number/name (Enter = all)")
        return V.category(raw) if raw else None

    def open_entry(self, pool):
        raw = self.ask("Enter an ID to read the steps (Enter = skip)")
        if not raw:
            return
        match = next((e for e in pool if str(e.id) == raw), None)
        if not match:
            print(f"{RED}x No such ID in this list.{RESET}")
            return
        ui.show_entry(self.repo.record_view(match.id))

    def search_screen(self):
        print(f"\n{BOLD}-- Search --{RESET}")
        text = self.ask("Describe the problem or keyword(s) (Enter = all)")
        cat = self.pick_category()
        min_sev = self.ask("Minimum severity 1-5 (Enter = 1)", V.severity, "1")
        results = self.search.search(text, cat, min_sev)
        ui.paginate(results, PAGE_SIZE)
        if results:
            self.open_entry(results)

    def browse(self):
        results = self.search.search()
        ui.paginate(results, PAGE_SIZE)
        self.open_entry(results)

    def emergency(self):
        print(f"\n{RED}{BOLD}-- Emergency quick list (call emergency services) --{RESET}")
        results = self.search.emergency_list()
        ui.paginate(results, PAGE_SIZE)
        self.open_entry(results)

    def add_entry(self):
        print(f"\n{BOLD}-- Add new first-aid entry --{RESET}")
        data = {}
        for f in V.FIELDS:
            if f.key == "category":
                self.show_categories()
            data[f.key] = self.ask(f.label, f.parse, date.today().isoformat() if f.key == "last_reviewed" else None)
        print(f"{GREEN}Saved entry #{self.repo.add(data).id}.{RESET}")

    def delete_entry(self):
        raw = self.ask("ID to delete (Enter = cancel)")
        entry = self.repo.get(int(raw)) if raw.isdigit() else None
        if not entry:
            print(f"{RED}x Not found.{RESET}" if raw else "Cancelled.")
        elif self.ask(f"Delete '{entry.title}'? (y/n)", V.yes_no):
            self.repo.delete(entry.id)
            print(f"{GREEN}Deleted.{RESET}")

    def show_summary(self):
        s = self.summary.compute()
        print("\n" + (summary_text(s) if s else f"{YELLOW}No data to summarise.{RESET}") + "\n")

    def show_warnings(self):
        alerts = self.warnings.check()
        print(f"\n{BOLD}-- Threshold warnings --{RESET}")
        for a in alerts:
            print(f"{YELLOW if a.kind == 'overdue' else RED}! {a.message}{RESET}")
        if not alerts:
            print(f"{GREEN}All clear.{RESET}")

    def chart(self):
        s = self.summary.compute()
        path = s and make_chart(s, self.repo.list_all(), REPORT_DIR)
        print(f"{GREEN}Chart saved to {path}{RESET}" if path else f"{YELLOW}Chart not created (no data, or run: pip install matplotlib).{RESET}")

    def export(self):
        s = self.summary.compute()
        if not s:
            print(f"{YELLOW}Nothing to export.{RESET}")
            return
        paths = export_all(s, self.repo.list_all(), REPORT_DIR)
        chart = make_chart(s, self.repo.list_all(), REPORT_DIR)
        print(f"{GREEN}Exported:{RESET}\n  " + "\n  ".join(paths + ([chart] if chart else [])))

    def import_csv(self):
        print(f"{DIM}Required columns: title,category,severity,keywords,steps,call_emergency (last_reviewed optional){RESET}")
        path = self.ask("CSV file path (Enter = cancel)")
        if not path:
            return
        try:
            result = CsvImporter(self.repo).run(path)
        except (OSError, ValueError) as e:
            print(f"{RED}x {e}{RESET}")
            return
        write_error_log(ERROR_LOG, path, result)
        print(f"{GREEN}Imported {result.added} row(s).{RESET} Rejected {len(result.errors)}." + (f" See {ERROR_LOG}" if result.errors else ""))
        for e in result.errors[:5]:
            print(f"  {YELLOW}{e}{RESET}")

    def run(self):
        ui.banner()
        n = len(self.warnings.check())
        print(f"{GREEN}Loaded {len(self.repo.list_all())} entries.{RESET}" + (f" {YELLOW}{n} warning(s) - see option 6.{RESET}" if n else ""))
        while True:
            print(MENU)
            choice = self.ask("Choose 0-10")
            if choice == "0":
                print("Stay safe! Goodbye.")
                return
            action = self.actions.get(choice)
            action() if action else print(f"{RED}x Please enter a number from 0 to 10.{RESET}")


def build_app(path=DATA_FILE):
    repo = JsonEntryRepository(path)
    warnings = WarningService(repo)
    return App(repo, SearchService(repo), warnings, SummaryService(repo, warnings))


def main():
    build_app().run()
