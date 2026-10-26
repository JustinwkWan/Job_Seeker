# Job search tracker

An automated job search for **new-grad / entry-level Software Engineer, AI/ML Engineer, and Backend** roles in
**Seattle, California, New York, and Remote (US)**.

- **Every weekday at ~11am PT**, a scheduled Claude run pulls new postings, reads the job descriptions,
  scores each one against `profile.md` with `rubric.md`, and commits a new file to `daily/`.
- **On the first weekday of each month**, it writes a trends report to `monthly/`: which skills are rising,
  what's new, eligibility patterns, pay, and what to do about it.

## Where to look
| File | What it is |
|---|---|
| `daily/YYYY-MM-DD.md` | That day's new postings, ranked: Apply today / Worth a look / Not eligible / Not read |
| `monthly/YYYY-MM.md` | Monthly skill-demand trends and recommendations |
| `resume-review.md` | Standing resume fixes and keywords you have but don't list |
| `rubric.md` | How jobs are scored (100 points + eligibility gate) |
| `profile.md` | Your targets and skills; **edit this when your resume changes** |
| `RUNBOOK.md` | Exact steps the scheduled runs follow; edit to change behavior |
| `data/jobs.csv` | Every posting seen (deduped), with extracted skills; feeds the monthly report |
| `data/skill_trends.csv` | Monthly skill counts for long-run trends |
| `scripts/fetch_listings.py` | Pulls and filters listings from SimplifyJobs/New-Grad-Positions |

## Sources
- [SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions), a community-maintained list updated daily
- Targeted web searches of Ashby, Greenhouse, Lever, and Amazon job boards for early-career roles the list misses

LinkedIn and Indeed aren't used; they block automated access.
