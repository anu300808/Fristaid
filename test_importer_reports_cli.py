import contextlib
import io
import os
import tempfile
import unittest
from unittest import mock

from firstaid_app.cli import App
from firstaid_app.importer import CsvImporter
from firstaid_app.repository import JsonEntryRepository
from firstaid_app.reports import export_all
from firstaid_app.services import SearchService, SummaryService, WarningService

HEADER = "title,category,severity,keywords,steps,call_emergency,last_reviewed\n"


class FileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = JsonEntryRepository(None)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        p = os.path.join(self.tmp.name, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def test_import_adds_good_rows_and_reports_bad_ones(self):
        before = len(self.repo.list_all())
        p = self.write("in.csv", HEADER
                       + "Frozen shoulder,Bones & Joints,2,shoulder,Rest it | Ice it for 15 min,n,\n"
                       + "Bad severity,Burns,7,burn,Cool it | Cover it loosely,n,\n"
                       + "Severe burn,Burns,5,burn,Cool it | Cover it loosely,y,\n")
        r = CsvImporter(self.repo).run(p)
        self.assertEqual(r.added, 1)
        self.assertEqual(len(self.repo.list_all()), before + 1)
        self.assertTrue(r.errors[0].startswith("Row 3") and "severity" in r.errors[0])
        self.assertIn("duplicate", r.errors[1])

    def test_import_rejects_missing_columns(self):
        with self.assertRaises(ValueError):
            CsvImporter(self.repo).run(self.write("bad.csv", "title,category\nA,B\n"))

    def test_import_missing_file(self):
        with self.assertRaises(OSError):
            CsvImporter(self.repo).run(os.path.join(self.tmp.name, "nope.csv"))

    def test_export_writes_three_report_files(self):
        wr = WarningService(self.repo)
        s = SummaryService(self.repo, wr).compute()
        paths = export_all(s, self.repo.list_all(), self.tmp.name)
        self.assertEqual(sorted(os.path.splitext(p)[1] for p in paths), [".csv", ".md", ".txt"])
        with open(paths[0], encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Executive Summary", text)


class CliTests(unittest.TestCase):
    def test_add_entry_loops_until_input_is_valid(self):
        repo = JsonEntryRepository(None)
        wr = WarningService(repo)
        app = App(repo, SearchService(repo), wr, SummaryService(repo, wr))
        before = len(repo.list_all())
        answers = iter(["3", "Test burn cream", "2", "9", "abc", "3", "cream,burn", "Cool the burn | Cover it loosely", "n", "", "0"])
        with mock.patch("builtins.input", lambda _="": next(answers)), contextlib.redirect_stdout(io.StringIO()) as out:
            app.run()
        self.assertEqual(len(repo.list_all()), before + 1)
        self.assertEqual(repo.list_all()[-1].severity, 3)
        self.assertIn("Severity must be between 1 and 5", out.getvalue())
        self.assertIn("whole number", out.getvalue())
