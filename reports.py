"""Report output. Each exporter renders one format; add a format by adding a subclass."""
import csv
import io
import os
from abc import ABC, abstractmethod
from collections import Counter
from datetime import date


def summary_text(s, markdown=False):
    h = (lambda t: f"## {t}") if markdown else (lambda t: f"{t}\n{'-' * len(t)}")
    L = [("# " if markdown else "") + "First-Aid Information Finder - Executive Summary", f"Generated: {s.generated}", "",
         h("Key figures"), f"- Total entries: {s.total}", f"- Average severity: {s.avg_severity:.2f} / 5",
         f"- Entries needing emergency call: {s.emergency} ({s.emergency / s.total:.0%})",
         f"- Average views per entry: {s.avg_views:.1f}", "", h("Entries by category")]
    for c, k in s.categories.most_common():
        L.append(f"- {c}: {k} (avg views {s.views_by_category[c] / k:.1f})")
    L += ["", h("Severity distribution")] + [f"- Level {i}: {s.severities.get(i, 0)}" for i in range(1, 6)]
    L += ["", h("Most viewed")] + [f"- {e.title} ({e.times_viewed} views)" for e in s.top]
    L += ["", h(f"Warnings ({len(s.alerts)})")] + ([f"- {a.message}" for a in s.alerts] or ["- None"])
    return "\n".join(L)


class Exporter(ABC):
    prefix, extension = "", ""

    @abstractmethod
    def render(self, summary, entries): ...

    def write(self, summary, entries, folder, stamp):
        path = os.path.join(folder, f"{self.prefix}_{stamp}.{self.extension}")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.render(summary, entries))
        return path


class MarkdownExporter(Exporter):
    prefix, extension = "summary", "md"
    def render(self, summary, entries): return summary_text(summary, markdown=True)


class TextExporter(Exporter):
    prefix, extension = "audit_log", "txt"
    def render(self, summary, entries): return summary_text(summary)


class CsvExporter(Exporter):
    prefix, extension = "records", "csv"

    def render(self, summary, entries):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "title", "category", "severity", "keywords", "steps", "call_emergency", "last_reviewed", "times_viewed"])
        for e in entries:
            w.writerow([e.id, e.title, e.category, e.severity, ";".join(e.keywords), e.steps, e.call_emergency, e.last_reviewed, e.times_viewed])
        return buf.getvalue()


EXPORTERS = (MarkdownExporter(), TextExporter(), CsvExporter())


def export_all(summary, entries, folder):
    os.makedirs(folder, exist_ok=True)
    stamp = f"{date.today():%Y%m%d}"
    return [x.write(summary, entries, folder, stamp) for x in EXPORTERS]


def make_chart(summary, entries, folder):
    """Save a 3-panel PNG. Returns its path, or None when Matplotlib is not installed."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    os.makedirs(folder, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(17, 5))
    cats = summary.categories.most_common()
    ax[0].barh([c for c, _ in cats][::-1], [k for _, k in cats][::-1], color="#e0527a")
    ax[0].set_title("Entries per category")
    ax[1].bar(range(1, 6), [summary.severities.get(i, 0) for i in range(1, 6)], color=["#3a9d5d", "#8bc34a", "#e6b01e", "#e67e22", "#d64545"])
    ax[1].set_title("Severity distribution")
    months = Counter(e.last_reviewed[:7] for e in entries)
    keys = sorted(months)
    ax[2].plot(keys, [months[k] for k in keys], marker="o", color="#5a3a29")
    ax[2].set_title("Entries reviewed per month (trend)")
    ax[2].tick_params(axis="x", rotation=70, labelsize=7)
    fig.suptitle("First-Aid Information Finder - Report", fontweight="bold")
    fig.tight_layout()
    path = os.path.join(folder, f"charts_{date.today():%Y%m%d}.png")
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path
