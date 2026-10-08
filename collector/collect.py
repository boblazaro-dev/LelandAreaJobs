#!/usr/bin/env python3
"""
Wilmington Area Jobs collector.

No Indeed or LinkedIn scraping.

This first version deliberately uses conservative extraction:
1. JSON feeds
2. RSS feeds
3. JSON-LD JobPosting records
4. source-specific adapters can be added later

The output is data/jobs.json for GitHub Pages.
"""

from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "collector" / "sources.json"
OUTPUT_FILE = ROOT / "data" / "jobs.json"

HEADERS = {
    "User-Agent": "Wilmington-Area-Jobs-Dashboard/1.0 (public local jobs research)"
}

ALLOWED_COUNTIES = {"Brunswick", "New Hanover", "Pender", "Regional"}

def clean(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()

def make_id(job):
    key = "|".join([
        clean(job.get("employer")).lower(),
        clean(job.get("title")).lower(),
        clean(job.get("location")).lower(),
        clean(job.get("url")).lower(),
    ])
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text, r.headers.get("content-type", "")

def parse_jsonld(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.get_text())
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "JobPosting":
                continue
            loc = item.get("jobLocation", {})
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            addr = loc.get("address", {}) if isinstance(loc, dict) else {}
            location = ", ".join(
                x for x in [
                    addr.get("addressLocality", ""),
                    addr.get("addressRegion", "")
                ] if x
            )
            employer = item.get("hiringOrganization", {})
            employer = employer.get("name", "") if isinstance(employer, dict) else employer
            salary = item.get("baseSalary", {})
            salary_text = ""
            if isinstance(salary, dict):
                val = salary.get("value", {})
                if isinstance(val, dict):
                    lo, hi = val.get("minValue"), val.get("maxValue")
                    unit = val.get("unitText", "")
                    if lo and hi:
                        salary_text = f"${lo}–${hi} {unit}".strip()
                    elif lo:
                        salary_text = f"${lo} {unit}".strip()
                elif val:
                    salary_text = str(val)

            jobs.append({
                "title": clean(item.get("title")),
                "employer": clean(employer),
                "location": clean(location),
                "county": "",
                "salary": clean(salary_text),
                "employment_type": clean(item.get("employmentType")),
                "date_posted": clean(item.get("datePosted")),
                "description": clean(BeautifulSoup(
                    item.get("description", ""), "html.parser"
                ).get_text(" ")),
                "url": urljoin(base_url, item.get("url") or base_url),
            })
    return jobs

def generic_html(source):
    html, _ = fetch(source["url"])
    return parse_jsonld(html, source["url"])

def ncworks_adapter(source):
    # NCWorks has a public search interface. A dedicated API/feed adapter
    # should be added after confirming the public endpoint/terms for the
    # desired query. We do not scrape Indeed or LinkedIn.
    return generic_html(source)

ADAPTERS = {
    "generic": generic_html,
    "ncworks": ncworks_adapter,
}

def normalize(job, source):
    job["source"] = source["name"]
    if not job.get("county"):
        job["county"] = source.get("county", "Regional")
    job["county"] = job["county"] if job["county"] in ALLOWED_COUNTIES else source.get("county", "Regional")
    job["id"] = make_id(job)
    job["collected_at"] = datetime.now(timezone.utc).isoformat()
    job["is_new"] = True
    return job

def load_existing():
    if not OUTPUT_FILE.exists():
        return {}
    try:
        data = json.loads(OUTPUT_FILE.read_text())
        return {x["id"]: x for x in data.get("jobs", []) if x.get("id")}
    except Exception:
        return {}

def main():
    sources = json.loads(SOURCE_FILE.read_text())
    old = load_existing()
    all_jobs = {}

    for source in sources:
        try:
            adapter = ADAPTERS[source.get("adapter", "generic")]
            jobs = adapter(source)
            for raw in jobs:
                if not raw.get("title"):
                    continue
                job = normalize(raw, source)
                if job["id"] in old:
                    job["first_seen"] = old[job["id"]].get("first_seen", old[job["id"]].get("collected_at"))
                    job["is_new"] = False
                else:
                    job["first_seen"] = job["collected_at"]
                all_jobs[job["id"]] = job
            print(f"{source['name']}: {len(jobs)} jobs")
        except Exception as exc:
            print(f"ERROR {source['name']}: {exc}")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": "Wilmington, NC",
        "counties": ["Brunswick", "New Hanover", "Pender"],
        "sources_excluded": ["Indeed", "LinkedIn"],
        "jobs": list(all_jobs.values())
    }
    result["jobs"].sort(key=lambda x: (x.get("date_posted", ""), x.get("employer", ""), x.get("title", "")), reverse=True)

    OUTPUT_FILE.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Wrote {len(result['jobs'])} jobs to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
