"""Build a fully static HTML site from the Financials web app.

Renders every page using the demo scenario (fictional data), rewrites internal
links to relative paths, disables interactive form elements, and writes the
output to _site/ for GitHub Pages deployment.

Usage:
    python scripts/build_static.py [--output _site]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Ensure the src package is importable when run from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from financials.demo_seeds import DEMO_SCENARIO_NAME, upsert_demo_scenario
from financials.schema import initialise_database
from financials.web import FinancialsWebApp

# ---------------------------------------------------------------------------
# Demo notice injected at the top of every page
# ---------------------------------------------------------------------------

_DEMO_NOTICE = (
    '<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:10px;'
    "padding:12px 16px;margin-bottom:18px;font-size:14px;color:#92400e\">"
    "<strong>📊 Demo preview</strong> — This is a static snapshot using sample "
    "data. Interactive features (forms, scenario switching) are not available here. "
    'Run the app locally to use the full tool.</div>'
)

# ---------------------------------------------------------------------------
# Link rewriting
# ---------------------------------------------------------------------------

# Map internal server paths to static file names.
_PAGE_MAP: dict[str, str] = {
    "/": "index.html",
    "/alex": "alex.html",
    "/charly": "charly.html",
    "/housing": "housing.html",
    "/plan": "plan.html",
    "/tracker": "tracker.html",
    "/variables": "variables.html",
    # Alias paths
    "/flat": "housing.html",
    "/sale": "housing.html",
    "/purchase": "housing.html",
    "/expenses": "tracker.html",
    "/manual-summaries": "tracker.html",
}

_HREF_RE = re.compile(r'href="(/[^"]*)"')
_ACTION_RE = re.compile(r'action="(/[^"]*)"')


def _rewrite_href(match: re.Match) -> str:  # type: ignore[type-arg]
    raw = match.group(1)
    # Strip query string to look up the base path.
    base = raw.split("?")[0]
    target = _PAGE_MAP.get(base)
    if target:
        return f'href="./{target}"'
    # Leave unknown paths as-is (e.g. external anchors, though none exist here).
    return match.group(0)


def rewrite_links(html: str) -> str:
    """Rewrite internal hrefs to relative static paths and neutralise form actions."""
    html = _HREF_RE.sub(_rewrite_href, html)
    # Forms won't work in a static context — point actions at '#' so browsers
    # don't navigate away on accidental submission.
    html = _ACTION_RE.sub('action="#"', html)
    return html


def inject_demo_notice(html: str) -> str:
    """Insert the demo notice banner right after the opening <main> tag."""
    return html.replace("<main>", f"<main>{_DEMO_NOTICE}", 1)


def postprocess(html: str) -> str:
    html = rewrite_links(html)
    html = inject_demo_notice(html)
    return html


# ---------------------------------------------------------------------------
# Page rendering
# ---------------------------------------------------------------------------

def build_site(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use an in-memory database so the build leaves no files on disk.
    # The anchor connection must stay open for the lifetime of the build:
    # closing the last connection to a shared in-memory database destroys it.
    db_path = ":memory:"
    anchor = initialise_database(db_path)
    upsert_demo_scenario(anchor)

    app = FinancialsWebApp(db_path)
    scenario = DEMO_SCENARIO_NAME

    pages: list[tuple[str, str]] = [
        ("index.html", app.render_summary(scenario)),
        ("alex.html", app.render_alex(scenario)),
        ("charly.html", app.render_charly(scenario)),
        # Render the flat tab for housing — most relevant for the demo.
        ("housing.html", app.render_housing(scenario, tab="flat")),
        # Render the flat tab for the budget plan.
        ("plan.html", app.render_plan(scenario, tab="flat")),
        ("tracker.html", app.render_tracker(scenario)),
        ("variables.html", app.render_variables(scenario)),
    ]

    for filename, html in pages:
        processed = postprocess(html)
        dest = output_dir / filename
        dest.write_text(processed, encoding="utf-8")
        print(f"  wrote {dest}")

    anchor.close()
    print(f"\nStatic site built → {output_dir.resolve()} ({len(pages)} pages)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="_site",
        metavar="DIR",
        help="Output directory (default: _site)",
    )
    args = parser.parse_args()
    build_site(Path(args.output))


if __name__ == "__main__":
    main()
