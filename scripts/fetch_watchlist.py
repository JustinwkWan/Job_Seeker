#!/usr/bin/env python3
"""Check the watchlist companies' own job boards for entry-level SWE / AI / backend roles.

Usage:
    python3 scripts/fetch_watchlist.py [--days N] [--out watchlist_candidates.json]

Companies and their job-board APIs live in data/watchlist.json. Supported board types:
  workday     POST https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
  greenhouse  GET  https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
  ashby       GET  https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true
Companies with "type": "search" have no public feed; the daily run looks them up with
WebSearch instead (see RUNBOOK.md).

Output has the same fields as fetch_listings.py plus `description` (plain text, trimmed),
`yoe_min` (smallest "N+ years" found), and `watchlist: true`, so most of these can be
scored without fetching the posting page. Postings already in data/jobs.csv are skipped.
"""
import argparse
import csv
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_listings import (EXCLUDE_TITLE, INCLUDE_TITLE, LEVEL_UP, job_key,  # noqa: E402
                            title_prescore)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(REPO_ROOT, "data", "watchlist.json")
JOBS_CSV = os.path.join(REPO_ROOT, "data", "jobs.csv")
PACIFIC = timezone(timedelta(hours=-7))
UA = {"User-Agent": "Mozilla/5.0 (job-search-tracker)", "Accept": "application/json"}

WORKDAY_QUERIES = ["software", "developer", "machine learning", "early career"]
# company boards use "engineer" for everything (thermal, process, solutions...), so require a software-ish title
SOFTWARE_TITLE = re.compile(
    r"\b(software|developer|sde|swe|programmer|machine learning|ml|ai|backend|back-end|full[- ]?stack|"
    r"platform|cloud|devops|site reliability|sre|infrastructure|data engineer|forward deploy\w*|"
    r"applications? engineer|web|api|distributed)\b", re.I)
NOT_FOR_JUSTIN = re.compile(
    r"\b(smts|lmts|pmts|active (ts|secret)|ts/sci|secret clearance|solutions? engineer|"
    r"systems engineer|process engineer|thermal|materials|avionics|propulsion|mid-level)\b", re.I)

SEATTLE = r"seattle|bellevue|redmond|kirkland|bothell|issaquah|sammamish|renton|everett|tacoma|" \
          r"lynnwood|woodinville|kent|tukwila|auburn|federal way|us-wa|, wa\b|washington state"
CALIF = r"california|\bca\b|us-ca|san francisco|bay area|san jose|sunnyvale|mountain view|palo alto|" \
        r"menlo park|santa clara|los angeles|irvine|san diego|el segundo|long beach|oakland|cupertino"
NEWYORK = r"new york|\bny\b|nyc|us-ny"
REMOTE_US = r"remote.{0,25}(us|usa|united states|u\.s\.)|(us|usa|united states).{0,25}remote|^remote$"


def buckets_for(text: str):
    t = text.lower()
    b = set()
    if re.search(SEATTLE, t):
        b.add("Seattle")
    if re.search(CALIF, t):
        b.add("California")
    if re.search(NEWYORK, t):
        b.add("New York")
    if re.search(REMOTE_US, t):
        b.add("Remote")
    return sorted(b)


def get_json(url, data=None, tries=2):
    body = json.dumps(data).encode() if data is not None else None
    headers = dict(UA)
    if body:
        headers["Content-Type"] = "application/json"
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(1.5)


def text_of(h: str) -> str:
    h = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", h or "", flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = html.unescape(t)  # greenhouse double-escapes
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", t)).strip()


def yoe_min(desc: str):
    vals = [int(m) for m in re.findall(r"(\d{1,2})\s*\+?\s*(?:or more\s*)?years?", desc, re.I) if int(m) < 20]
    return min(vals) if vals else None


def posted_days_ago(s: str):
    s = (s or "").lower()
    if "today" in s:
        return 0
    if "yesterday" in s:
        return 1
    m = re.search(r"(\d+)\+?\s*days", s)
    return int(m.group(1)) if m else None


def title_ok(title: str) -> bool:
    if NOT_FOR_JUSTIN.search(title) or not SOFTWARE_TITLE.search(title):
        return False
    if EXCLUDE_TITLE.search(title) or not INCLUDE_TITLE.search(title):
        return False
    if LEVEL_UP.search(title) and not re.search(r"new grad|early career|university", title, re.I):
        return False
    return True


# ---------------- board fetchers -> list of dict ----------------
def fetch_workday(c, days):
    tenant, wd, sites = c["tenant"], c["wd"], c["sites"]
    out, seen_paths = [], set()
    for site in sites:
        base = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}"
        for q in WORKDAY_QUERIES:
            for offset in range(0, 100, 20):
                d = get_json(f"{base}/jobs", {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": q})
                posts = d.get("jobPostings", [])
                for p in posts:
                    path = p.get("externalPath")
                    if not path or path in seen_paths:
                        continue
                    age = posted_days_ago(p.get("postedOn"))
                    if age is None or age > days or not title_ok(p.get("title", "")):
                        continue
                    seen_paths.add(path)
                    out.append((base, site, p, age))
                if len(posts) < 20:
                    break
    jobs = []
    for base, site, p, age in out:
        try:
            info = get_json(f"{base}{p['externalPath']}").get("jobPostingInfo", {})
        except Exception:
            continue
        locs = [info.get("location", "")] + list(info.get("additionalLocations", []) or [])
        desc = text_of(info.get("jobDescription", ""))
        remote = info.get("remoteType", "") or ""
        loc_text = " | ".join(locs) + (" | remote united states" if "remote" in remote.lower() and "united states" in str(info.get("country", "")).lower() else "")
        jobs.append(dict(
            id=f"wd-{c['tenant']}-{info.get('jobReqId') or p['externalPath']}", company=c["name"],
            title=info.get("title", p.get("title", "")), locations=[l for l in locs if l], loc_text=loc_text,
            url=info.get("externalUrl") or f"https://{c['tenant']}.{c['wd']}.myworkdayjobs.com/{site}{p['externalPath']}",
            date_posted=(datetime.now(PACIFIC).date() - timedelta(days=age)).isoformat(),
            description=desc, salary=""))
    return jobs


def fetch_greenhouse(c, days):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{c['board']}/jobs?content=true")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    jobs = []
    for j in d.get("jobs", []):
        ts = j.get("first_published") or j.get("updated_at")
        try:
            when = datetime.fromisoformat(ts)
        except Exception:
            continue
        if when < cutoff or not title_ok(j.get("title", "")):
            continue
        loc = (j.get("location") or {}).get("name", "")
        offices = "; ".join(o.get("name", "") for o in j.get("offices", []) or [])
        jobs.append(dict(
            id=f"gh-{c['board']}-{j['id']}", company=c["name"], title=j["title"],
            locations=[l.strip() for l in loc.split(";") if l.strip()], loc_text=f"{loc} | {offices}",
            url=j.get("absolute_url", ""), date_posted=when.astimezone(PACIFIC).date().isoformat(),
            description=text_of(j.get("content", "")), salary=""))
    return jobs


def fetch_ashby(c, days):
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{c['board']}?includeCompensation=true")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    jobs = []
    for j in d.get("jobs", []):
        try:
            when = datetime.fromisoformat(j.get("publishedAt", "").replace("Z", "+00:00"))
        except Exception:
            continue
        if when < cutoff or not title_ok(j.get("title", "")):
            continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations", []) or []]
        comp = (j.get("compensation") or {}).get("compensationTierSummary", "") or ""
        jobs.append(dict(
            id=f"ash-{c['board']}-{j['id']}", company=c["name"], title=j["title"],
            locations=[l for l in locs if l], loc_text=" | ".join(locs) + (" | remote united states" if j.get("isRemote") else ""),
            url=j.get("jobUrl", ""), date_posted=when.astimezone(PACIFIC).date().isoformat(),
            description=j.get("descriptionPlain", "") or text_of(j.get("descriptionHtml", "")), salary=comp))
    return jobs


FETCHERS = {"workday": fetch_workday, "greenhouse": fetch_greenhouse, "ashby": fetch_ashby}


def load_seen():
    seen = set()
    if os.path.exists(JOBS_CSV):
        with open(JOBS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                seen.add(row["id"])
                seen.add(job_key(row["company"], row["title"]))
                seen.add(row.get("url", ""))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7,
                    help="posted within N days (default 7; company boards are slower-moving than the lists)")
    ap.add_argument("--out", default="watchlist_candidates.json")
    args = ap.parse_args()

    wl = json.load(open(WATCHLIST))
    seen = load_seen()
    out, report = [], {}
    for c in wl["companies"]:
        f = FETCHERS.get(c["type"])
        if not f:
            continue
        try:
            jobs = f(c, args.days)
        except Exception as e:
            report[c["name"]] = f"ERROR {type(e).__name__}: {e}"
            continue
        kept = 0
        for j in jobs:
            b = buckets_for(j.pop("loc_text"))
            if not b or j["id"] in seen or j["url"] in seen or job_key(j["company"], j["title"]) in seen:
                continue
            y = yoe_min(j["description"])
            if y is not None and y >= 3:
                continue
            j.update(location_buckets=b, yoe_min=y, category="", sources=["watchlist"], watchlist=True,
                     title_prescore=title_prescore(j["title"]) + 2,  # watchlist boost
                     description=j["description"][:6000])
            out.append(j)
            kept += 1
        report[c["name"]] = f"{len(jobs)} recent matching titles, {kept} kept"
    out.sort(key=lambda j: ("Seattle" in j["location_buckets"], j["title_prescore"], j["date_posted"]), reverse=True)
    with open(args.out, "w") as fh:
        json.dump(out, fh, indent=1)
    for k, v in report.items():
        print(f"  {k:24s} {v}", file=sys.stderr)
    print(f"{len(out)} watchlist candidates -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
