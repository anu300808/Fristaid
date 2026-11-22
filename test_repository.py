import os
import tempfile
import unittest

from firstaid_app.repository import JsonEntryRepository

SAMPLE = dict(title="Test entry", category="Other", severity=2, keywords=["test"],
              steps="Do one thing | Do another", call_emergency=False, last_reviewed="2026-01-01")


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "data.json")

    def tearDown(self):
        self.tmp.cleanup()

    def repo(self):
        return JsonEntryRepository(self.path, notify=lambda m: None)

    def test_missing_file_is_created_with_seed_data(self):
        self.assertGreaterEqual(len(self.repo().list_all()), 30)
        self.assertTrue(os.path.exists(self.path))

    def test_added_entry_survives_restart(self):
        e = self.repo().add(SAMPLE)
        self.assertIn(e.id, [x.id for x in self.repo().list_all()])

    def test_corrupt_json_is_backed_up_and_reseeded(self):
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertGreaterEqual(len(self.repo().list_all()), 30)
        self.assertTrue(os.path.exists(self.path + ".corrupt"))

    def test_wrong_record_shape_is_rejected(self):
        with open(self.path, "w") as f:
            f.write('[{"id": 1}]')
        self.assertGreaterEqual(len(self.repo().list_all()), 30)

    def test_delete_and_get(self):
        r = self.repo()
        e = r.add(SAMPLE)
        self.assertTrue(r.delete(e.id))
        self.assertIsNone(r.get(e.id))
        self.assertFalse(r.delete(e.id))

    def test_record_view_counts_and_persists(self):
        r = self.repo()
        e = r.add(SAMPLE)
        r.record_view(e.id)
        self.assertEqual(self.repo().get(e.id).times_viewed, 1)

    def test_in_memory_repository_never_touches_disk(self):
        r = JsonEntryRepository(None)
        r.add(SAMPLE)
        self.assertFalse(os.path.exists(self.path))
