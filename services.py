"""Business logic: ranked fuzzy search, pluggable warning rules, summary statistics."""
import difflib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from .config import OVERDUE_DAYS

_words = lambda text: set(re.findall(r"[a-z0-9]+", text.lower()))


def _score_term(term, e):
    """5 title word, 4 keyword, 3 prefix, 2 close spelling (typo), 1 found in the steps, 0 no match."""
    title_w = _words(e.title)
    key_w = {w for k in e.keywords for w in _words(k)}
    pool = title_w | key_w
    if term in title_w:
        return 5
    if term in key_w:
        return 4
    if len(term) >= 3 and any(w.startswith(term) for w in pool):
        return 3
    if len(term) >= 4 and difflib.get_close_matches(term, pool, n=1, cutoff=0.75):
        return 2
    return 1 if term in _words(e.steps) else 0


class SearchService:
    def __init__(self, repo):
        self._repo = repo

    def search(self, text="", category=None, min_severity=1):
        """Every word must match something. Results are ranked; emergencies get a small boost."""
        terms, ranked = sorted(_words(text)), []
        for e in self._repo.list_all():
            if (category and e.category != category) or e.severity < min_severity:
                continue
            scores = [_score_term(t, e) for t in terms]
            if any(s == 0 for s in scores):
                continue
            ranked.append((sum(scores) + (1 if e.call_emergency else 0), e))
        ranked.sort(key=lambda p: (-p[0], -p[1].severity, p[1].title))
        return [e for _, e in ranked]

    def emergency_list(self):
        return sorted((e for e in self._repo.list_all() if e.call_emergency), key=lambda e: (-e.severity, e.title))


@dataclass(frozen=True)
class Alert:
    kind: str
    entry_id: int
    message: str


# Each rule is a small function (entry, today) -> Alert | None. Add a rule by appending one to the list.
def overdue_review(e, today, limit=OVERDUE_DAYS):
    age = e.days_since_review(today)
    if age > limit:
        return Alert("overdue", e.id, f"OVERDUE REVIEW: #{e.id} {e.title} (last reviewed {age} days ago)")


def severe_without_call(e, today):
    if e.severity == 5 and not e.call_emergency:
        return Alert("anomaly", e.id, f"ANOMALY: #{e.id} {e.title} is severity 5 but has no emergency call flag")


def emergency_but_minor(e, today):
    if e.call_emergency and e.severity <= 2:
        return Alert("anomaly", e.id, f"ANOMALY: #{e.id} {e.title} flagged emergency but severity is only {e.severity}")


DEFAULT_RULES = (overdue_review, severe_without_call, emergency_but_minor)


class WarningService:
    def __init__(self, repo, rules=DEFAULT_RULES):
        self._repo, self._rules = repo, rules

    def check(self, today=None):
        today = today or date.today()
        return [a for e in self._repo.list_all() for rule in self._rules if (a := rule(e, today))]


@dataclass
class Summary:
    total: int
    avg_severity: float
    avg_views: float
    emergency: int
    categories: Counter
    severities: Counter
    views_by_category: dict
    top: list
    alerts: list
    generated: str


class SummaryService:
    def __init__(self, repo, warnings):
        self._repo, self._warnings = repo, warnings

    def compute(self):
        items = self._repo.list_all()
        if not items:
            return None
        views = defaultdict(int)
        for e in items:
            views[e.category] += e.times_viewed
        n = len(items)
        return Summary(
            total=n, avg_severity=sum(e.severity for e in items) / n, avg_views=sum(e.times_viewed for e in items) / n,
            emergency=sum(e.call_emergency for e in items), categories=Counter(e.category for e in items),
            severities=Counter(e.severity for e in items), views_by_category=dict(views),
            top=sorted(items, key=lambda e: -e.times_viewed)[:5], alerts=self._warnings.check(),
            generated=datetime.now().strftime("%Y-%m-%d %H:%M"))
