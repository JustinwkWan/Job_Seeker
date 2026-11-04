# Runbook

The scheduled tasks follow this file. Edit it to change how the search behaves.

---

## Daily run (every day, ~10:45am Pacific)

**Freshness rule — the core of this search.** Justin only wants postings **from the last 24 hours**, measured by
the **company's own posting date**, not the date a job list picked it up. "Fresh" means posted since the previous
day's run: a timestamp within 24 hours of now, or, where only a date is shown, today or yesterday (Pacific).
A job list adding a req that the company posted weeks ago is **stale**, and stale postings are dropped: not scored,
not shown, just counted. If a page shows no posting date at all, fall back to the list's date and say so.
The run is daily, weekends included, so nothing ages out between runs.

**Excluded companies:** skip every company listed in `data/excluded_companies.json` (currently Amazon/AWS,
TikTok and ByteDance). `fetch_listings.py` drops them automatically; also leave them out of web searches,
the "Not read yet" table, and every section of the daily file.

**Blocked websites:** never visit or link any site in `data/blocked_sites.json` (currently jobright.ai).
Don't WebFetch a URL on those domains, pass them as `blocked_domains` on **every** WebSearch, and never use
one as a job's link anywhere in the daily file. `fetch_listings.py` blanks candidate URLs on blocked sites
(`url: ""`). For those postings (mostly the ones sourced from jobright), go to the **company's own careers
site / ATS** instead and read, date-check and score the job from there: search `"<company>" "<exact title>"`
restricted to the ATS domains plus the company's careers domain (if you don't know it, one WebSearch for
`"<company>" careers` finds it), and use that official page as the job's link. The jobright GitHub list (github.com)
is still used as a candidate source; only jobright.ai itself is blocked.

**No reading cap.** Read the description of **every** fresh candidate. Don't stop at a quota; this run is
allowed to take longer and use more compute. Batch the work: several WebSearch / WebFetch calls per turn
in parallel, or split the candidate list across subagents.

1. **Pull candidates**
   ```bash
   python3 scripts/fetch_listings.py --days 1 --out /tmp/candidates.json
   ```
   This clones seven community job lists from GitHub (SimplifyJobs, vanshb03, speedyapply SWE + AI, jobright,
   resumax, dreamworkhq),
   keeps postings the lists date today or yesterday that match the roles and locations in `profile.md`,
   merges the same job listed in several places, and drops anything already in `data/jobs.csv`.
   The list date is only a first filter; step 3 checks the company's own date.

1b. **Check the watchlist companies** (`data/watchlist.json`, ~20 Seattle-area employers Justin picked)
   ```bash
   python3 scripts/fetch_watchlist.py --days 1 --out /tmp/watchlist.json
   ```
   This queries Workday, Greenhouse, and Ashby boards directly (exact first-published timestamps on
   Greenhouse/Ashby) and returns entry-level software roles in his locations **with the full job description
   included**, so score these from the `description` field without fetching the page. Watchlist jobs go first
   and are labeled ⭐ Watchlist in the daily file. Takes ~2 minutes. For each `"type": "search"` company
   (Meta, Google, Stripe, Uber, Oracle, PACCAR, Alaska Airlines, Costco, Redfin), run one WebSearch such as
   `"<company>" software engineer (new grad OR "early career" OR "entry level" OR university) Seattle`
   with `allowed_domains` set to that company's `domains`, and keep only postings from the last 24 hours.
   If a board errors, note it in the daily file and continue.

1c. **Wider net: plain Software Engineer / Backend Engineer roles** (`data/boards.json`, ~120 tech-company boards)
   ```bash
   python3 scripts/fetch_watchlist.py --file data/boards.json --days 1 --out /tmp/boards.json
   ```
   Same script and output fields as 1b, but over a wider set of Greenhouse / Ashby / Lever boards, and these
   jobs are **not** labeled ⭐ Watchlist (source `boards`). Titles don't need "new grad" or "I": any software /
   backend / full-stack / AI-ML engineer title without a senior qualifier (Senior, Staff, Principal, Lead, III+)
   is checked. **Experience rule:** the script drops a posting whose description asks for more than 2 years
   (`MAX_YOE = 2`). When you score one, confirm the required years yourself: keep it only if the *required*
   experience is 2 years or less (0–2, 1+, 2+, "2–4" all pass; 3+ goes under Not eligible). A posting that names
   no years and no level is scored as 0–2 years (level fit 17) and flagged "no level stated". Takes ~1–2 minutes.
   To add a company, copy an entry in `data/boards.json` (the slug is in its job-board URL).

2. **Supplementary searches (3–5 WebSearch calls)** for early-career roles the lists miss, restricted to
   ATS domains (`jobs.ashbyhq.com`, `job-boards.greenhouse.io`, `jobs.lever.co`), e.g.:
   - "Software Engineer I" Seattle
   - "AI Engineer" entry level OR "0-2 years"
   - "Backend Engineer" new grad remote
   - "Software Engineer I" New York
   - "Machine Learning Engineer I" California
   - "Software Engineer" "0-2 years" OR "1+ years" Seattle
   - "Backend Engineer" "0-2 years" OR "1+ years of experience"
   Search results carry no dates, so open each hit that isn't already in `data/jobs.csv` and keep it only
   if its posting date is within the last 24 hours.

3. **Read every fresh candidate's job description.** Watchlist and boards jobs already carry their description
   (score them from it). Watchlist jobs first, then Seattle and Remote, then the
   rest by `title_prescore`. Job URLs from the candidates file can't be fetched directly; for each, WebSearch
   `"<company>" "<exact title>"` with `allowed_domains` set to the ATS domains above plus the company's careers
   domain if known (e.g. pinterestcareers.com, careersatdoordash.com, careers.microsoft.com), then WebFetch the
   matching result. If no official page turns up, retry once without `allowed_domains` (still with the blocked
   sites as `blocked_domains`); an aggregator copy (builtin, techstars, anitab, freehire, employbl,
   general-catalyst/8vc job boards) is fine, but check the location matches and use the company's posting date,
   not the aggregator's. Never fall back to a blocked site.
   - **First check the posting date.** Older than 24 hours → **stale**: stop reading, record it, move on.
   - If a page won't load or has no requirements text after the retry, list it under "Not read yet"
     (with no link if the only one found is on a blocked site).
   - Otherwise extract: posting date, required quals, preferred quals, YOE, degree, graduation window,
     location, salary, clearance/export control, and every named technology.

4. **Score** each fresh posting you read with `rubric.md` against `profile.md`. Apply the eligibility gate first.
   A class-of-2027 graduation window is **not** a gate: score it (level fit 15) and add the 🎓 flag.

5. **Write `daily/YYYY-MM-DD.md`** using the layout of the most recent file in `daily/`:
   summary line (candidates pulled, fresh, stale dropped, read, scored) → **Apply today** (**every** job scoring 80+,
   best first; no cap and no topping up with lower scores, so if nothing hits 80, say so) → **Worth a look** →
   **Stretch / Skip** → **Not eligible** (reason) → **Not read yet** (every fresh posting whose page couldn't be read,
   as a table) → **Resume notes** (keyword gaps that showed up in 2+ postings today).
   - **At most 3 jobs per company across the scored tiers** (Apply today / Worth a look / Stretch). Show that
     company's best 3 there; put the rest in a compact **More from <company>** table (score, title, location, link,
     one-line note) right after Stretch / Skip.
   - **Stale postings aren't shown.** Give one line: "N stale postings dropped (company date older than 24h)".
   - Each job in Apply today and Worth a look: company, title, score, location, salary, posted date, apply link,
     a one-line score breakdown, why it fits, matched keywords, missing keywords split into "you have it, add it"
     vs "true gap", and one resume tweak. Lower tiers can be table rows.
   - If no fresh postings turned up at all, still write the file saying so.

6. **Append every posting you looked at to `data/jobs.csv`**: scored, not eligible, not read yet, **and stale**
   (tier `Stale`, `jd_read=no`, `flags` = the company's posting date). Recording stale ones keeps them from being
   re-read tomorrow. Columns:
   `date_found,id,company,title,location_bucket,locations,url,date_posted,category,jd_read,eligible,score,tier,yoe_required,grad_window,salary,skills,missing_keywords,flags,source`
   - `date_posted`: the company's posting date when you found one, otherwise the list's date.
   - `skills`: semicolon-separated **canonical** names (vocabulary below) of every technology the JD names. Empty if not read.
   - `missing_keywords`: canonical names from the JD that are not on the resume.
   - `source`: semicolon-separated list from the candidate's `sources` (`simplify`, `vansh`, `speedyapply`, `speedyapply-ai`, `jobright`, `resumax`, `dreamworkhq`, `watchlist`, `boards`), or `search`.
   - resumax mixes new-grad and experienced roles, so apply the 2-years-or-less rule strictly there. dreamworkhq links go to
     dreamworkhq.com pages: use them to read the JD if needed, but link the company's own posting when you can find it.
   - `flags`: include `class-of-2027 window` when it applies, so the monthly report can track it.
   - Use Python's `csv` module to append; never hand-edit quoting.

7. **Commit and push**: `git add -A && git commit -m "Daily search YYYY-MM-DD: N fresh, M scored" && git pull --rebase && git push`.

8. **Notify** with the count of fresh postings, how many scored 80+, and the top 3 with scores and links.

---

## Monthly run (first weekday of the month)

1. Load `data/jobs.csv`. Use rows with `jd_read=yes` from the previous calendar month for skill stats,
   all non-`Stale` rows for volume stats (rows before 2026-11-04 used a 4-day window, so say so when comparing). Compare against the month before when it exists.
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
