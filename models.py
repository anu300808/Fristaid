from dataclasses import dataclass, fields, asdict
from datetime import date, datetime


@dataclass
class Entry:
    id: int
    title: str
    category: str
    severity: int
    keywords: list
    steps: str
    call_emergency: bool
    last_reviewed: str
    times_viewed: int = 0

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ValueError("Record must be an object")
        names = [f.name for f in fields(cls)]
        for n in names:
            if n not in d and n != "times_viewed":
                raise ValueError(f"Record missing '{n}'")
        return cls(**{n: d[n] for n in names if n in d})

    def to_dict(self):
        return asdict(self)

    @property
    def step_list(self):
        return [s.strip() for s in self.steps.split("|") if s.strip()]

    def days_since_review(self, today=None):
        return ((today or date.today()) - datetime.strptime(self.last_reviewed, "%Y-%m-%d").date()).days
