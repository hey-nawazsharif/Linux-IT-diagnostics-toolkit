"""Explicit, local HTML/JSON report export; never writes to a network service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .render import render_html


def write_report(report: dict[str, Any], directory: Path) -> tuple[Path, Path]:
    output = Path(directory)
    if not output.is_dir() and output.exists():
        raise ValueError("Report destination is not a directory")
    page = output / "index.html"
    # Do not clobber the static GitHub Pages demo, even if the user chose docs/.
    if page.exists() and 'id="seed-report"' in page.read_text(encoding="utf-8")[:35000]:
        raise ValueError(
            "This folder contains the interactive OpsPulse dashboard. "
            "Please choose a different destination such as reports."
        )
    output.mkdir(parents=True, exist_ok=True)
    json_file = output / "report.json"
    json_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    page.write_text(render_html(report), encoding="utf-8")
    return json_file, page
