#!/usr/bin/env python3
"""Pull new-grad / entry-level listings from several community-maintained GitHub lists,
filter to Justin's roles and locations, drop anything already seen, and pre-score by title
so the agent knows which postings to read in full.

Usage:
    python3 scripts/fetch_listings.py [--days N] [--out candidates.json]

Sources (all GitHub repos, updated daily):
  simplify    SimplifyJobs/New-Grad-Positions        (.github/scripts/listings.json)
  vansh       vanshb03/New-Grad-2027                 (.github/scripts/listings.json, same schema)
  speedyapply speedyapply/2026-SWE-College-Jobs      (NEW_GRAD_USA.md table; has salary)
  jobright    jobright-ai/2026-Software-Engineer-New-Grad (README.md table; large, noisy)

The same job often appears in several lists; it is merged into one candidate and every
source is recorded. Does NOT write jobs.csv: the agent appends after reading/scoring.
"""
import argparse
import csv
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOBS_CSV = os.path.join(REPO_ROOT, "data", "jobs.csv")
EXCLUDED_JSON = os.path.join(REPO_ROOT, "data", "excluded_companies.json")
PACIFIC = timezone(timedelta(hours=-8))  # date math only; a day either way doesn't matter

SOURCES = {
    "simplify": "https://github.com/SimplifyJobs/New-Grad-Positions.git",
    "vansh": "https://github.com/vanshb03/New-Grad-2027.git",
    "speedyapply": "https://github.com/speedyapply/2026-SWE-College-Jobs.git",
    "jobright": "https://github.com/jobright-ai/2026-Software-Engineer-New-Grad.git",
}

# ---------- location filter: Seattle area, California, New York, Remote (US) ----------
SEATTLE_AREA = {
    "seattle", "bellevue", "redmond", "kirkland", "bothell", "issaquah", "sammamish",
    "renton", "everett", "tacoma", "lynnwood", "woodinville", "kent", "tukwila",
}
CA_SHORT = {"sf", "south sf", "la", "california", "bay area", "sf bay area"}


def location_bucket(loc: str):
    l = loc.strip().lower()
    city = l.split(",")[0].strip()
    if city in SEATTLE_AREA and (", wa" in l or "washington" in l or l == city):
        return "Seattle"
    if l in CA_SHORT or l.endswith(", ca") or ", ca," in l or "california" in l:
        return "California"
    if (l in {"nyc", "new york"} or l.endswith(", ny") or ", ny," in l
            or "new york" in l):
        return "New York"
    if l in {"remote in usa", "remote in us", "remote", "united states", "usa", "us",
             "remote, united states", "united states (remote)"}:
        return "Remote"
    return None


# ---------- role filter ----------
SIMPLIFY_CATEGORIES = {"Software", "Software Engineering", "AI/ML/Data",
                       "Data Science, AI & Machine Learning"}
EXCLUDE_TITLE = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|intern(ship)?|co-?op|"
    r"phd|ph\.d|postdoc|hardware|electrical|mechanical|firmware|fpga|asic|rf|analog|"
    r"verification|technician|sales|recruit|marketing|accountant|clearance|ts/sci|"
    r"analyst(?!.*engineer)|research scientist|data scientist|annotator|teleoperator|"
    r"temporary|part[- ]time|contract|master'?s|embedded|mainframe|salesforce|sap|"
    r"servicenow developer|qa|test engineer|support engineer|helpdesk|seasonal|quality assurance|military)\b",
    re.I)
# level II+ titles are usually 2+ years, unless the title itself says new grad / early career
LEVEL_UP = re.compile(r"\b(ii|iii|iv|2|3)\b(?!.*\b(new grad|early career|university)\b)", re.I)
INCLUDE_TITLE = re.compile(r"\b(engineer|engineering|developer|sde|swe|programmer|resident)\b", re.I)

# title keywords -> rough relevance (pre-score only; the real score comes from the JD)
TITLE_BOOST = [
    (r"\b(ai|ml|machine learning|llm|genai|generative|applied ai|agent|agentic)\b", 3),
    (r"\b(backend|back-end|platform|infrastructure|distributed|cloud|api)\b", 3),
    (r"\b(software (engineer|developer)|swe|sde|software development engineer)\b", 2),
    (r"\bfull[- ]?stack\b", 2),
    (r"\bforward deployed\b", 1),
    (r"\bsecurity\b", 1),
    (r"\b(new grad|university|graduate|entry|early career|associate|junior|jr\.?)\b", 2),
    (r"\b(engineer|developer|sde|swe) (i|1)\b", 2),
    (r"\bdata (scientist|analyst)\b", -2),
    (r"\b(mobile|ios|android|frontend|front-end)\b", -1),
]


def title_prescore(title: str) -> int:
    return sum(w for pat, w in TITLE_BOOST if re.search(pat, title, re.I))


def norm(s: str) -> str:
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(inc|llc|corp|corporation|co|ltd|technologies|the)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


TITLE_STOPWORDS = {
    "new", "grad", "grads", "graduate", "college", "ncg", "university", "early", "career",
    "campus", "start", "remote", "the", "and", "of", "us", "usa", "full", "time", "fulltime",
    "hybrid", "onsite", "entry", "level",
}


def job_key(company: str, title: str) -> str:
    """Company + order-free set of meaningful title words, so the same job listed as
    'Full Stack SWE, New Grad - Quora (Remote)' and 'Full Stack SWE New Grad' match."""
    c = norm(company)
    words = re.findall(r"[a-z0-9+#]+", title.lower().replace("&", "and"))
    toks = set()
    for w in words:
        w = {"1": "i", "one": "i", "2": "ii", "sde": "software", "swe": "software",
             "dev": "developer", "eng": "engineer", "development": "developer"}.get(w, w)
        if w in TITLE_STOPWORDS or re.fullmatch(r"20\d\d", w) or norm(w) == c:
            continue
        toks.add(w)
    return c + "|" + " ".join(sorted(toks))


def load_seen():
    seen = set()
    if os.path.exists(JOBS_CSV):
        with open(JOBS_CSV, newline="") as f:
            for row in csv.DictReader(f):
                seen.add(row["id"])
                seen.add(job_key(row["company"], row["title"]))
    return seen


def load_excluded():
    """Company-name regex for data/excluded_companies.json (None if the file is missing or empty)."""
    if not os.path.exists(EXCLUDED_JSON):
        return None
    with open(EXCLUDED_JSON) as f:
        pats = [c["match"] for c in json.load(f).get("companies", []) if c.get("match")]
    return re.compile("|".join(f"(?:{p})" for p in pats), re.I) if pats else None


def clone(url: str) -> str:
    d = tempfile.mkdtemp(prefix="jobs_")
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, d], check=True)
    return d


# ---------- per-source parsers -> list of dict(company,title,locations,url,date_posted,salary,id,category) ----------
def parse_listings_json(path, source):
    out = []
    for x in json.load(open(path)):
        if not x.get("active") or not x.get("is_visible", True):
            continue
        cat = x.get("category")
        if cat and cat not in SIMPLIFY_CATEGORIES:
            continue
        out.append(dict(
            id=x["id"], company=x["company_name"], title=x.get("title", ""),
            locations=x.get("locations", []), url=x.get("url", ""), category=cat or "",
            date_posted=datetime.fromtimestamp(x.get("date_posted", 0), timezone.utc).date(),
            salary="", source=source))
    return out


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_speedyapply(path):
    out, today = [], datetime.now(PACIFIC).date()
    for line in open(path, encoding="utf-8"):
        if not line.startswith("| <a") and not line.startswith("| **"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) not in (5, 6):
            continue
        company, title, loc = strip_tags(cells[0]), strip_tags(cells[1]), strip_tags(cells[2])
        salary = strip_tags(cells[3]) if len(cells) == 6 else ""
        m = re.search(r'href="([^"]+)"', cells[-2])
        age = re.match(r"(\d+)d", strip_tags(cells[-1]))
        if not m or not age:
            continue
        out.append(dict(
            id="sa-" + norm(m.group(1))[-24:], company=company, title=title,
            locations=[l.strip() for l in re.split(r"<br\s*/?>|;", cells[2]) if l.strip()] or [loc],
            url=m.group(1), category="", salary=salary, source="speedyapply",
            date_posted=today - timedelta(days=int(age.group(1)))))
    return out


def parse_jobright(path):
    out, year, company = [], datetime.now(PACIFIC).year, None
    for line in open(path, encoding="utf-8"):
        if not line.startswith("| **[") and not line.startswith("| ↳"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            continue
        if cells[0] != "↳":
            m = re.match(r"\*\*\[(.+?)\]", cells[0])
            company = m.group(1) if m else strip_tags(cells[0])
        t = re.match(r"\*\*\[(.+?)\]\((.+?)\)\*\*", cells[1])
        if not t or not company:
            continue
        try:
            posted = datetime.strptime(f"{cells[4]} {year}", "%b %d %Y").date()
        except ValueError:
            continue
        loc = cells[2]
        if cells[3].lower() == "remote" and "united states" in loc.lower():
            loc = "Remote"
        out.append(dict(
            id="jr-" + t.group(2).split("/info/")[-1].split("?")[0], company=company,
            title=t.group(1), locations=[loc], url=t.group(2), category="", salary="",
            source="jobright", date_posted=posted))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=4, help="look back this many days (4 covers weekends)")
    ap.add_argument("--out", default="candidates.json")
    args = ap.parse_args()

    raw = []
    for name, url in SOURCES.items():
        try:
            d = clone(url)
            if name in ("simplify", "vansh"):
                raw += parse_listings_json(os.path.join(d, ".github/scripts/listings.json"), name)
            elif name == "speedyapply":
                raw += parse_speedyapply(os.path.join(d, "NEW_GRAD_USA.md"))
            elif name == "jobright":
                raw += parse_jobright(os.path.join(d, "README.md"))
        except Exception as e:  # one broken source shouldn't kill the run
            print(f"WARNING: source {name} failed: {e}", file=sys.stderr)

    seen = load_seen()
    excluded = load_excluded()
    cutoff = datetime.now(PACIFIC).date() - timedelta(days=args.days)
    merged = {}
    for x in raw:
        if x["date_posted"] < cutoff:
            continue
        title = x["title"]
        if excluded and excluded.search(x["company"].strip()):
            continue
        if EXCLUDE_TITLE.search(title) or not INCLUDE_TITLE.search(title):
            continue
        if LEVEL_UP.search(title) and not re.search(r"new grad|early career|university", title, re.I):
            continue
        buckets = sorted({b for b in (location_bucket(l) for l in x["locations"]) if b})
        if not buckets:
            continue
        key = job_key(x["company"], title)
        if x["id"] in seen or key in seen:
            continue
        if key in merged:  # same job from another list: merge
            m = merged[key]
            m["sources"] = sorted(set(m["sources"]) | {x["source"]})
            m["location_buckets"] = sorted(set(m["location_buckets"]) | set(buckets))
            m["salary"] = m["salary"] or x["salary"]
            # prefer a direct ATS link over an aggregator/redirect link
            if ("jobright.ai" in m["url"] or "go.vansh" in m["url"]) and not (
                    "jobright.ai" in x["url"] or "go.vansh" in x["url"]):
                m["url"] = x["url"]
            continue
        merged[key] = dict(
            id=x["id"], company=x["company"], title=title, category=x["category"],
            locations=x["locations"], location_buckets=buckets, url=x["url"],
            date_posted=x["date_posted"].isoformat(), salary=x["salary"],
            sources=[x["source"]], title_prescore=title_prescore(title))

    out = list(merged.values())
    # rank: title relevance, then how many lists carry it (signal of a real, open posting), then recency
    out.sort(key=lambda j: (j["title_prescore"], len(j["sources"]), j["date_posted"]), reverse=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    by_src = {}
    for j in out:
        for s in j["sources"]:
            by_src[s] = by_src.get(s, 0) + 1
    print(f"{len(out)} new candidate postings -> {args.out}  (by source: {by_src})", file=sys.stderr)


if __name__ == "__main__":
    main()
