# Runbook

The scheduled tasks follow this file. Edit it to change how the search behaves.

---

## Daily run (weekdays, ~11am Pacific)

1. **Pull candidates**
   ```bash
   python3 scripts/fetch_listings.py --days 4 --out /tmp/candidates.json
   ```
   This clones SimplifyJobs/New-Grad-Positions, keeps active postings from the last 4 days that match
   the roles and locations in `profile.md`, and drops anything already in `data/jobs.csv`.
   Use `--days 4` so Monday's run covers the weekend.

2. **Supplementary searches (3–5 WebSearch calls).** The Simplify list skews toward "2027 New Grad"
   roles, which often exclude a June 2026 graduate. Search for early-career roles it misses, restricting
   to ATS domains (`jobs.ashbyhq.com`, `job-boards.greenhouse.io`, `jobs.lever.co`, `amazon.jobs`), e.g.:
   - "Software Engineer I" Seattle
   - "AI Engineer" entry level OR "0-2 years"
   - "Backend Engineer" new grad remote
   - "Software Engineer I" New York
   - "Machine Learning Engineer I" California
   Add only postings from the last ~7 days that aren't already in `data/jobs.csv`.

3. **Read job descriptions.** Read up to **15** postings, highest `title_prescore` first, skipping
   obvious mismatches. Job URLs from the candidates file can't be fetched directly; for each, WebSearch
   `"<company> <title>"` with `allowed_domains` set to the ATS domains above (add the company's careers
   domain if known), then WebFetch the matching result. If the official page isn't found, an aggregator
   copy (builtin, techstars, anitab, freehire, employbl) is fine; note if it's an older or closed copy.
   Extract: required quals, preferred quals, YOE, degree, **graduation window**, location, salary,
   clearance/export control, and every named technology.

4. **Score** each read posting with `rubric.md` against `profile.md`. Apply the eligibility gate first.

5. **Write `daily/YYYY-MM-DD.md`** using the layout of the most recent file in `daily/`:
   summary line → **Apply today** → **Worth a look** → **Stretch / Skip** → **Not eligible** (reason) →
   **Not read yet** (title-only table) → **Resume notes** (keyword gaps that showed up in 2+ postings today).
   Each scored job: company, title, score, location, salary, posted date, apply link, a one-line score
   breakdown, why it fits, matched keywords, missing keywords split into "you have it, add it" vs
   "true gap", and one resume tweak. If nothing new was found, still write the file saying so.

6. **Append every posting from today to `data/jobs.csv`** (read or not, so nothing repeats tomorrow).
   Columns:
   `date_found,id,company,title,location_bucket,locations,url,date_posted,category,jd_read,eligible,score,tier,yoe_required,grad_window,salary,skills,missing_keywords,flags,source`
   - `skills`: semicolon-separated **canonical** names (vocabulary below) of every technology the JD names. Empty if not read.
   - `missing_keywords`: canonical names from the JD that are not on the resume.
   - `source`: `simplify` or `search`.
   - Use Python's `csv` module to append; never hand-edit quoting.

7. **Commit and push**: `git add -A && git commit -m "Daily search YYYY-MM-DD: N new, M scored" && git push`.

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
