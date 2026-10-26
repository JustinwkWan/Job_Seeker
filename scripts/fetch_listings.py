#!/usr/bin/env python3
"""Pull new-grad listings, filter to Justin's roles/locations, drop ones already seen,
and pre-score by title so the agent knows which postings to read in full.

Usage:
    python3 scripts/fetch_listings.py [--days N] [--out candidates.json]

Source: SimplifyJobs/New-Grad-Positions (community list, updated daily on GitHub).
Writes candidates JSON (newest + best-title-match first). Does NOT write jobs.csv;
the agent appends to jobs.csv after scoring, so the CSV only ever holds scored jobs.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_CSV = os.path.join(REPO_ROOT, "data", "jobs.csv")
SOURCE_REPO = "https://github.com/SimplifyJobs/New-Grad-Positions.git"
LISTINGS_PATH = ".github/scripts/listings.json"

# ---------- location filter: Seattle area, California, New York, Remote (US) ----------
SEATTLE_AREA = {
    "seattle", "bellevue", "redmond", "kirkland", "bothell", "issaquah", "sammamish",
    "renton", "everett", "tacoma", "lynnwood", "woodinville", "kent", "tukwila",
}
CA_SHORT = {"sf", "south sf", "la", "california", "bay area", "sf bay area"}


def location_bucket(loc: str):
    l = loc.strip().lower()
    city = l.split(",")[0].strip()
    if city in SEATTLE_AREA and (", wa" in l or l == city):
        return "Seattle"
    if l in CA_SHORT or l.endswith(", ca") or ", ca," in l:
        return "California"
    if l in {"nyc", "new york"} or l.endswith(", ny") or ", ny," in l or "new york" in l:
        return "New York"
    if l in {"remote in usa", "remote in us", "remote", "united states", "usa", "us"}:
        return "Remote"
    return None


# ---------- role filter ----------
ROLE_CATEGORIES = {"Software", "Software Engineering", "AI/ML/Data",
                   "Data Science, AI & Machine Learning"}
EXCLUDE_TITLE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|intern(ship)?|co-?op|"
    r"phd|ph\.d|postdoc|hardware|electrical|mechanical|firmware|fpga|asic|rf |analog|"
    r"verification|technician|sales|recruit|marketing|accountant|clearance|ts/sci|"
    r"analyst(?!.*engineer)|research scientist|data scientist|annotator|teleoperator)\b",
    re.I)
# title must look like an engineering role
INCLUDE_TITLE = re.compile(r"\b(engineer|engineering|developer|sde|swe|programmer|resident)\b", re.I)

# title keywords -> rough relevance (pre-score only; real score comes from the JD)
TITLE_BOOST = [
    (r"\b(ai|ml|machine learning|llm|genai|generative|applied ai|agent)", 3),
    (r"\bbackend|back-end|platform|infrastructure|distributed|cloud|api\b", 3),
    (r"\bsoftware (engineer|developer)|swe\b", 2),
    (r"\bfull[- ]?stack\b", 2),
    (r"\bsecurity\b", 1),
    (r"\bnew grad|university|graduate|entry|early career|associate|engineer i\b|\bi\b$", 2),
    (r"\bdata (scientist|analyst)\b", -2),
    (r"\bembedded|mobile|ios|android\b", -1),
]


def title_prescore(title: str) -> int:
    s = 0
    for pat, w in TITLE_BOOST:
        if re.search(pat, title, re.I):
            s += w
    return s


def load_seen():
    seen = set()
    if os.path.exists(JOBS_CSV):
        with open(JOBS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                seen.add(row["id"])
                # also dedupe re-posts of the same role at the same company
                seen.add((row["company"].lower(), row["title"].lower()))
    return seen


def fetch_listings():
    tmp = tempfile.mkdtemp(prefix="simplify_")
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", SOURCE_REPO, tmp], check=True)
    with open(os.path.join(tmp, LISTINGS_PATH)) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=4,
                    help="look back this many days (default 4 covers weekends)")
    ap.add_argument("--out", default="candidates.json")
    args = ap.parse_args()

    listings = fetch_listings()
    seen = load_seen()
    cutoff = time.time() - args.days * 86400
    out = []
    for x in listings:
        if not x.get("active") or not x.get("is_visible", True):
            continue
        if x.get("date_posted", 0) < cutoff:
            continue
        if x.get("category") not in ROLE_CATEGORIES:
            continue
        title = x.get("title", "")
        if EXCLUDE_TITLE.search(title) or not INCLUDE_TITLE.search(title):
            continue
        if x["id"] in seen or (x["company_name"].lower(), title.lower()) in seen:
            continue
        buckets = sorted({b for b in (location_bucket(l) for l in x.get("locations", [])) if b})
        if not buckets:
            continue
        out.append({
            "id": x["id"],
            "company": x["company_name"],
            "title": title,
            "category": x.get("category"),
            "locations": x.get("locations", []),
            "location_buckets": buckets,
            "url": x["url"],
            "date_posted": datetime.fromtimestamp(x["date_posted"], timezone.utc).strftime("%Y-%m-%d"),
            "sponsorship": x.get("sponsorship", ""),
            "degrees": x.get("degrees", []),
            "title_prescore": title_prescore(title),
        })

    out.sort(key=lambda j: (j["title_prescore"], j["date_posted"]), reverse=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"{len(out)} new candidate postings -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
