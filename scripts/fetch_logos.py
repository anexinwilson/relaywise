"""Download app logos into the frontend so nothing is fetched from Composio at runtime.

The catalog is a fixed, committed list, so its logos may as well be committed
too. They are ~1-2 KB SVGs; the whole set is smaller than a single photo.

This removes a third-party request from every render of the integrations page,
works offline, and means a Composio CDN outage cannot blank the UI.

Run after regenerating apps_catalog.json:

    python scripts/fetch_logos.py
"""

from __future__ import annotations

import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
CATALOG = ROOT / "frontend" / "src" / "apps_catalog.json"
LOGO_DIR = ROOT / "frontend" / "public" / "logos"
TOOLKITS = ROOT / "backend" / "src" / "agent" / "toolkits.json"
PUBLIC_PREFIX = "/logos"
TIMEOUT = 20

EXTENSION_BY_TYPE = {
    "image/svg+xml": ".svg",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
}


def download(app: dict) -> tuple[str, str | None]:
    slug = app["slug"]
    source = app.get("logo") or ""
    if not source.startswith("http"):
        return slug, None  # already local

    try:
        response = requests.get(source, timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - reported, not fatal
        print(f"  !! {slug}: {exc}")
        return slug, None

    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    extension = EXTENSION_BY_TYPE.get(content_type)
    if extension is None:
        print(f"  !! {slug}: unexpected content-type {content_type!r}")
        return slug, None

    path = LOGO_DIR / f"{slug}{extension}"
    path.write_bytes(response.content)
    return slug, f"{PUBLIC_PREFIX}/{slug}{extension}"


def main() -> int:
    apps = json.loads(CATALOG.read_text(encoding="utf-8"))
    LOGO_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {len(apps)} logos into {LOGO_DIR.relative_to(ROOT)}")
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = dict(pool.map(download, apps))

    rewritten = 0
    for app in apps:
        local = results.get(app["slug"])
        if local:
            app["logo"] = local
            rewritten += 1

    CATALOG.write_text(json.dumps(apps, indent=2) + "\n", encoding="utf-8")

    failed = len(apps) - rewritten
    print(f"\n{rewritten} logos stored locally, {failed} left pointing at their origin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
