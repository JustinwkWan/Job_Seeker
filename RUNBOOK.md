# Runbook

The scheduled tasks follow this file. Edit it to change how the search behaves.

---

## Daily run (weekdays, ~11am Pacific)

**Excluded companies:** skip every company listed in `data/excluded_companies.json` (currently Amazon/AWS and
TikTok). `fetch_listings.py` drops them automatically; also leave them out of web searches,
the "Not read yet" table, and every section of the daily file.

1. **Pull candidates**
   ```bash
   python3 scripts/fetch_listings.py --days 4 --out /tmp/candidates.json
   ```
   This clones four community job lists from GitHub (SimplifyJobs, vanshb03, speedyapply, jobright),
   keeps postings from the last 4 days that match the roles and locations in `profile.md`, merges the
   same job listed in several places, and drops anything already in `data/jobs.csv`. Expect roughly
   100–150 candidates; `--days 4` lets Monday's run cover the weekend.

1b. **Check the watchlist companies** (`data/watchlist.json`, ~20 Seattle-area employers Justin picked)
   ```bash
   python3 scripts/fetch_watchlist.py --days 7 --out /tmp/watchlist.json
   ```
   This queries Workday, Greenhouse, and Ashby boards directly and returns entry-level software roles in
   his locations **with the full job description included**, so score these from the `description`
   field without fetching the page. Watchlist jobs go first in the reading order and are labeled
   ⭐ Watchlist in the daily file. Takes ~2 minutes. For each `"type": "search"` company (Meta, Google,
   Stripe, Uber, Oracle, PACCAR, Alaska Airlines, Costco, Redfin), run one WebSearch such as
   `"<company>" software engineer (new grad OR "early career" OR "entry level" OR university) Seattle`
   with `allowed_domains` set to that company's `domains`, and add any posting from the last ~7 days.
   If a board errors, note it in the daily file and continue.

2. **Supplementary searches (3–5 WebSearch calls)** for early-career roles the lists miss, restricted to
   ATS domains (`jobs.ashbyhq.com`, `job-boards.greenhouse.io`, `jobs.lever.co`), e.g.:
   - "Software Engineer I" Seattle
   - "AI Engineer" entry level OR "0-2 years"
   - "Backend Engineer" new grad remote
   - "Software Engineer I" New York
   - "Machine Learning Engineer I" California
   Add only postings from the last ~7 days that aren't already in `data/jobs.csv`.

3. **Read job descriptions — target 5–8 "Apply today" jobs.** Work down the candidates in order
   (`title_prescore`, then number of lists carrying it), preferring Seattle and Remote, and read
   **at most 3 postings per company per day** so one big hirer can't crowd out the rest.
   Stop once **8 jobs score 80+** or you've read **30** descriptions. Job URLs from the candidates file
   can't be fetched directly; for each, WebSearch `"<company>" "<exact title>"` with `allowed_domains` set to
   the ATS domains above plus the company's careers domain if known (e.g.
   pinterestcareers.com, careersatdoordash.com, careers.microsoft.com), then WebFetch the matching result.
   If no official page turns up, retry once without `allowed_domains`; an aggregator copy (builtin,
   techstars, anitab, freehire, employbl, general-catalyst/8vc job boards) is fine, but note if it's an older or
   closed copy and check the location matches. If a page has no requirements text, move on.
   Extract: required quals, preferred quals, YOE, degree, graduation window, location, salary,
   clearance/export control, and every named technology.

4. **Score** each read posting with `rubric.md` against `profile.md`. Apply the eligibility gate first.
   A class-of-2027 graduation window is **not** a gate: score it (level fit 15) and add the 🎓 flag.

5. **Write `daily/YYYY-MM-DD.md`** using the layout of the most recent file in `daily/`:
   summary line → **Apply today** (5–8, best first) → **Worth a look** → **Stretch / Skip** →
   **Not eligible** (reason) → **Not read yet** (top ~15 unread by title, as a table) →
   **Resume notes** (keyword gaps that showed up in 2+ postings today).
   Each scored job: company, title, score, location, salary, posted date, apply link, a one-line score
   breakdown, why it fits, matched keywords, missing keywords split into "you have it, add it" vs
   "true gap", and one resume tweak. If nothing new was found, still write the file saying so.

6. **Append every posting that appears in today's file to `data/jobs.csv`** (scored, not eligible, or in
   the "Not read yet" table) so it doesn't repeat tomorrow. Candidates that weren't shown at all are
   **not** recorded; they stay eligible for tomorrow's run while they're inside the 4-day window.
   Columns:
   `date_found,id,company,title,location_bucket,locations,url,date_posted,category,jd_read,eligible,score,tier,yoe_required,grad_window,salary,skills,missing_keywords,flags,source`
   - `skills`: semicolon-separated **canonical** names (vocabulary below) of every technology the JD names. Empty if not read.
   - `missing_keywords`: canonical names from the JD that are not on the resume.
   - `source`: semicolon-separated list from the candidate's `sources` (`simplify`, `vansh`, `speedyapply`, `jobright`), or `search`.
   - `flags`: include `class-of-2027 window` when it applies, so the monthly report can track it.
   - Use Python's `csv` module to append; never hand-edit quoting.

7. **Commit and push**: `git add -A && git commit -m "Daily search YYYY-MM-DD: N new, M scored" && git pull --rebase && git push`.

---

## Monthly run (first weekday of the month)

1. Load `data/jobs.csv`. Use rows with `jd_read=yes` from the previous calendar month for skill stats,
   all rows for volume stats. Compare against the month before when it exists.
2. Write `monthly/YYYY-MM.md` (the month being reviewed) with:
   - **Volume:** postings found, read, eligible; split by role type and location bucket; top hiring companies
   - **Skill demand:** top 25 canonical skills by share of read postings, with change vs last month (▲/▼ points)
   - **What's new:** skills that appeared for the first time or rose ≥5 points; new tools added to the vocabulary
   - **Eligibility trends:** share of postings that excluded a June 2026 grad, required MS, or wanted 2+ years
   - **Pay:** median posted base salary by location bucket where listed
   - **What this means for Justin:** 3–5 concrete actions (skill to learn, keyword to add, project to build, role type to prioritize)
   - Note sample size; call a change a trend only with ≥20 read postings in both months.
3. Append that month's skill counts to `data/skill_trends.csv`: `month,skill,count,share,read_postings`.
4. If any recommendation changes how Justin should be scored, propose an edit to `profile.md` in the
   report instead of changing it silently.
5. Commit and push: `git commit -m "Monthly trends YYYY-MM"`.

---

## Canonical skill vocabulary
Map JD wording to these names (lowercase). If a JD names a tool not listed, add it as a new lowercase
name and list it under "new tools" in that day's file; that is how new trends surface.

**Languages:** python, java, typescript, javascript, c++, c, go, rust, scala, kotlin, c#, ruby, swift, sql, bash
**Web / backend:** react, node.js, nest.js, next.js, django, flask, fastapi, spring, graphql, rest-apis, grpc, websockets, html, css
**Data:** mysql, postgresql, nosql, mongodb, redis, dynamodb, kafka, spark, airflow, snowflake, arrow, parquet, iceberg, elasticsearch
**Cloud / infra:** aws, gcp, azure, docker, kubernetes, terraform, ci-cd, github-actions, linux, prometheus, grafana, observability
**AI / ML:** llm, rag, agents, langchain, langgraph, mcp, vector-db, embeddings, prompt-engineering, evals, fine-tuning, pytorch, tensorflow, jax, cuda, ml-infra, inference, ai-assisted-dev, openai-api, claude-api, hugging-face
**Systems / CS:** distributed-systems, concurrency, data-structures-algorithms, operating-systems, networking, compilers, databases-internals, performance, security
**Practices:** testing, code-review, agile, on-call, system-design
