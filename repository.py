"""Storage layer. Services depend on EntryRepository, not on JSON, so storage can be swapped (e.g. SQLite)."""
import json
import os
import shutil
from abc import ABC, abstractmethod

from .models import Entry
from .seed import seed_entries


class EntryRepository(ABC):
    @abstractmethod
    def list_all(self): ...
    @abstractmethod
    def get(self, entry_id): ...
    @abstractmethod
    def add(self, data): ...
    @abstractmethod
    def delete(self, entry_id): ...
    @abstractmethod
    def record_view(self, entry_id): ...


class JsonEntryRepository(EntryRepository):
    """JSON file store. path=None keeps everything in memory (used by tests)."""

    def __init__(self, path=None, seed_factory=seed_entries, notify=print):
        self.path, self._notify = path, notify
        self._items = self._load(seed_factory)

    def _load(self, seed_factory):
        if not self.path:
            return seed_factory()
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Top-level JSON must be a list")
            return [Entry.from_dict(r) for r in data]
        except FileNotFoundError:
            self._notify("No data file found - creating a fresh seeded dataset.")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            shutil.copy(self.path, self.path + ".corrupt")
            self._notify(f"Data file unreadable ({e}). Backed up to {self.path}.corrupt; reseeding.")
        self._items = seed_factory()
        self._save()
        return self._items

    def _save(self):
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._items], f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)  # atomic swap: a crash never leaves a half-written file

    def list_all(self):
        return list(self._items)

    def get(self, entry_id):
        return next((e for e in self._items if e.id == entry_id), None)

    def add(self, data):
        entry = Entry(id=max((e.id for e in self._items), default=0) + 1, times_viewed=0, **data)
        self._items.append(entry)
        self._save()
        return entry

    def delete(self, entry_id):
        e = self.get(entry_id)
        if e:
            self._items.remove(e)
            self._save()
        return e is not None

    def record_view(self, entry_id):
        e = self.get(entry_id)
        if e:
            e.times_viewed += 1
            self._save()
        return e
