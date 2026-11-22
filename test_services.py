import unittest
from datetime import date

from firstaid_app.models import Entry
from firstaid_app.repository import JsonEntryRepository
from firstaid_app.services import SearchService, SummaryService, WarningService


def e(i, title, cat="Burns", sev=2, kw=("x",), steps="Do something useful now", call=False, rev="2026-06-01", views=0):
    return Entry(i, title, cat, sev, list(kw), steps, call, rev, views)


def repo_with(*entries):
    return JsonEntryRepository(None, seed_factory=lambda: list(entries))


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.repo = repo_with(
            e(1, "Severe bleeding", "Bleeding & Wounds", 5, ("blood",), call=True),
            e(2, "Minor burn", "Burns", 1, ("burn",), steps="Cool it, then stop any bleeding nearby"),
            e(3, "Sprain", "Bones & Joints", 2, ("ankle",)),
        )
        self.s = SearchService(self.repo)

    def ids(self, *a, **k):
        return [x.id for x in self.s.search(*a, **k)]

    def test_title_match_outranks_steps_match(self):
        self.assertEqual(self.ids("bleeding"), [1, 2])

    def test_keyword_match(self):
        self.assertEqual(self.ids("ankle"), [3])

    def test_typo_is_still_found(self):
        self.assertEqual(self.ids("bleding")[0], 1)

    def test_prefix_match(self):
        self.assertEqual(self.ids("spr"), [3])

    def test_every_word_must_match(self):
        self.assertEqual(self.ids("minor ankle"), [])

    def test_category_and_severity_filters(self):
        self.assertEqual(self.ids("", category="Burns"), [2])
        self.assertEqual(self.ids("", min_severity=3), [1])

    def test_empty_search_lists_emergencies_first(self):
        self.assertEqual(self.ids("")[0], 1)

    def test_emergency_list_sorted_by_severity(self):
        self.assertEqual([x.id for x in self.s.emergency_list()], [1])


class WarningTests(unittest.TestCase):
    TODAY = date(2026, 11, 22)

    def test_flags_overdue_and_anomalies(self):
        repo = repo_with(e(1, "Old", rev="2024-01-01"), e(2, "Bad five", sev=5, call=False),
                         e(3, "Odd call", sev=1, call=True), e(4, "Fine", sev=3, call=True))
        kinds = {a.entry_id: a.kind for a in WarningService(repo).check(self.TODAY)}
        self.assertEqual(kinds, {1: "overdue", 2: "anomaly", 3: "anomaly"})

    def test_custom_rule_can_be_plugged_in(self):
        from firstaid_app.services import Alert
        rule = lambda ent, today: Alert("custom", ent.id, "hi") if ent.title == "Fine" else None
        self.assertEqual(len(WarningService(repo_with(e(1, "Fine")), rules=(rule,)).check()), 1)


class SummaryTests(unittest.TestCase):
    def test_numbers(self):
        repo = repo_with(e(1, "A", sev=5, call=True, views=4), e(2, "B", sev=1, views=2), e(3, "C", "Other", 3, views=0))
        s = SummaryService(repo, WarningService(repo)).compute()
        self.assertEqual((s.total, s.emergency), (3, 1))
        self.assertAlmostEqual(s.avg_severity, 3.0)
        self.assertAlmostEqual(s.avg_views, 2.0)
        self.assertEqual(s.categories["Burns"], 2)
        self.assertEqual(s.top[0].title, "A")

    def test_empty_repository_gives_none(self):
        repo = repo_with()
        self.assertIsNone(SummaryService(repo, WarningService(repo)).compute())
