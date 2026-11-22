"""First-Aid Information Finder as a FastHTML web app.  Run:  python web.py   ->  http://localhost:5001
Reuses the same layers as the terminal app (repository, services, validators, exporters).
Educational tool, not medical advice: in an emergency call your local emergency number."""
from fasthtml.common import *
from datetime import date
from starlette.responses import RedirectResponse, Response

from firstaid_app.config import CATEGORIES, DATA_FILE
from firstaid_app.repository import JsonEntryRepository
from firstaid_app.reports import EXPORTERS
from firstaid_app.services import SearchService, SummaryService, WarningService
from firstaid_app.validators import validate_row

repo = JsonEntryRepository(DATA_FILE)
warner = WarningService(repo)
searcher = SearchService(repo)
summarizer = SummaryService(repo, warner)

STYLE = Style("""
.badge{display:inline-block;padding:2px 10px;border-radius:999px;font-size:.75rem;font-weight:700;color:#fff;margin-right:6px}
.sev1,.sev2{background:#2e9e57}.sev3{background:#d98a14}.sev4,.sev5{background:#d64545}
.call{background:#fff0f0;color:#b32020;border:1px solid #f0b4b4;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:700}
.call-banner{background:#d64545;color:#fff;padding:12px 16px;border-radius:10px;font-weight:700;margin-bottom:14px}
.errors{color:#b32020}.muted{color:#777}
.barrow{display:grid;grid-template-columns:200px 1fr 40px;gap:10px;align-items:center;margin:6px 0;font-size:.9rem}
.bar{background:#eee;border-radius:999px;height:12px;overflow:hidden}.bar>div{background:#e0527a;height:100%}
nav a{margin-right:14px}
""")
app, rt = fast_app(hdrs=(STYLE,))


def page(title, *body):
    nav = Nav(A("Search", href="/"), A("Emergency list", href="/emergency"), A("Add topic", href="/add"), A("Summary", href="/summary"))
    return Title(f"{title} | First-Aid Finder"), Main(nav, H1(title), *body, cls="container")


def badge(e):
    return Span(f"Severity {e.severity}", cls=f"badge sev{e.severity}")


def results_view(entries):
    if not entries:
        return P("No matching topics.", cls="muted")
    return Div(*[Article(
        A(Strong(e.title), href=f"/entry/{e.id}"), " ",
        Span("CALL EMERGENCY", cls="call") if e.call_emergency else None,
        Div(badge(e), Small(e.category))) for e in entries])


@rt("/")
def get(q: str = "", category: str = "", min_sev: int = 1):
    form = Form(
        Input(type="search", name="q", value=q, autofocus=True, placeholder="Describe the problem, e.g. burn, bleding, chest pain"),
        Div(Select(Option("All categories", value=""), *[Option(c, value=c, selected=(c == category)) for c in CATEGORIES], name="category"),
            Select(*[Option(f"Severity {i}+", value=str(i), selected=(i == min_sev)) for i in range(1, 6)], name="min_sev"), cls="grid"),
        hx_get="/results", hx_trigger="input changed delay:250ms, change, submit", hx_target="#results")
    return page("First-Aid Information Finder", form, Div(results_view(searcher.search(q, category or None, min_sev)), id="results"))


@rt("/results")
def get(q: str = "", category: str = "", min_sev: int = 1):
    return results_view(searcher.search(q, category or None, min_sev))


@rt("/emergency")
def get():
    return page("Emergency quick list", P("Call emergency services first for these.", cls="muted"), results_view(searcher.emergency_list()))


@rt("/entry/{id}")
def get(id: int):
    e = repo.record_view(id)
    if not e:
        return page("Not found", P("No such topic."), A("Back to search", href="/"))
    return page(e.title,
        Div("CALL EMERGENCY SERVICES", cls="call-banner") if e.call_emergency else None,
        P(badge(e), e.category, f" · reviewed {e.last_reviewed}"),
        Ol(*[Li(s) for s in e.step_list]),
        P(Small("Keywords: " + ", ".join(e.keywords))),
        Form(Button("Delete this topic", cls="secondary outline"), method="post", action=f"/entry/{e.id}/delete",
             onsubmit="return confirm('Delete this topic?')"))


@rt("/entry/{id}/delete")
def post(id: int):
    repo.delete(id)
    return RedirectResponse("/", status_code=303)


def add_form(v=None, errors=()):
    v = v or {}
    return Form(
        Ul(*[Li(e) for e in errors], cls="errors") if errors else None,
        Label("Title", Input(name="title", value=v.get("title", ""), required=True)),
        Label("Category", Select(*[Option(c, value=c, selected=(c == v.get("category"))) for c in CATEGORIES], name="category")),
        Label("Severity 1 (minor) to 5 (life-threatening)", Input(name="severity", type="number", min="1", max="5", value=v.get("severity", "1"))),
        Label("Keywords (comma separated)", Input(name="keywords", value=v.get("keywords", ""), required=True)),
        Label("Steps (separate with  | )", Textarea(v.get("steps", ""), name="steps", rows="4", required=True)),
        Label("Call emergency services?", Select(Option("No", value="n"), Option("Yes", value="y", selected=v.get("call_emergency") == "y"), name="call_emergency")),
        Label("Last reviewed", Input(name="last_reviewed", type="date", max=date.today().isoformat(), value=v.get("last_reviewed") or date.today().isoformat())),
        Button("Save topic"), method="post", action="/add")


@rt("/add")
def get():
    return page("Add a first-aid topic", add_form())


@rt("/add")
def post(title: str = "", category: str = "", severity: str = "", keywords: str = "", steps: str = "",
         call_emergency: str = "n", last_reviewed: str = ""):
    raw = dict(title=title, category=category, severity=severity, keywords=keywords, steps=steps,
               call_emergency=call_emergency, last_reviewed=last_reviewed or date.today().isoformat())
    clean, errors = validate_row(raw)  # same rules as the terminal app and the CSV import
    if errors:
        return page("Add a first-aid topic", add_form(raw, errors))
    return RedirectResponse(f"/entry/{repo.add(clean).id}", status_code=303)


def bars(counter):
    top = max(counter.values())
    return [Div(Span(str(k)), Div(Div(style=f"width:{v / top * 100:.0f}%"), cls="bar"), Span(str(v)), cls="barrow") for k, v in counter.items()]


@rt("/summary")
def get():
    s = summarizer.compute()
    if not s:
        return page("Executive summary", P("No data yet."))
    stat = lambda label, val: Article(H3(str(val)), Small(label))
    return page("Executive summary",
        Div(stat("Topics", s.total), stat("Average severity", f"{s.avg_severity:.2f}"), stat("Need emergency call", s.emergency),
            stat("Avg views", f"{s.avg_views:.1f}"), cls="grid"),
        H3("Topics by category"), *bars(dict(s.categories.most_common())),
        H3("Severity distribution"), *bars({f"Level {i}": s.severities.get(i, 0) for i in range(1, 6)}),
        H3("Most viewed"), Ul(*[Li(A(e.title, href=f"/entry/{e.id}"), f" ({e.times_viewed})") for e in s.top]),
        H3(f"Warnings ({len(s.alerts)})"), Ul(*[Li(a.message) for a in s.alerts]) if s.alerts else P("All clear.", cls="muted"),
        H3("Download report"), Div(*[A(x.extension.upper(), href=f"/export/{x.extension}", role="button", cls="outline") for x in EXPORTERS], cls="grid"))


MEDIA = {"md": "text/markdown", "txt": "text/plain", "csv": "text/csv"}


@rt("/export/{kind}")
def get(kind: str):
    exporter = next((x for x in EXPORTERS if x.extension == kind), None)
    s = summarizer.compute()
    if not exporter or not s:
        return Response("Not found", status_code=404)
    return Response(exporter.render(s, repo.list_all()), media_type=MEDIA[kind] + "; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="firstaid_report.{kind}"'})


serve()
