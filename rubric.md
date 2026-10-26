# Scoring rubric

Every job whose description was read gets a **Fit Score out of 100**, built from what recruiters
and applicant-tracking systems actually screen on. Jobs whose description could not be read are
listed separately and not scored.

## Step 0 — Eligibility gate (pass / fail, checked first)
A failing job is listed under **Not eligible** with the reason and not scored.

| Check | Fails when |
|---|---|
| Degree | Requires an MS or PhD |
| Experience | Requires 3+ years |
| Clearance | Requires an *active* security clearance (eligibility to obtain one is only a flag) |
| Location | The job isn't actually in Seattle / California / New York / Remote US once you read it |
| Posting status | Page says it's closed / no longer accepting applications |

**Graduation window is not a gate.** A posting that asks for a later graduation date (e.g. "Fall 2026 –
Summer 2027", "May 2027 or later", "2027 Start") is scored normally and flagged
**🎓 Class-of-2027 window**. Most application forms still let a June 2026 graduate submit, so apply
and let the recruiter decide.

Soft flags (scored, but called out): 🎓 class-of-2027 window, US-person / export-control requirement,
clearance eligibility, no visa sponsorship, on-site only, travel >25%.

## Step 1 — Score (100 points)

| Criterion | Pts | How it's scored |
|---|---|---|
| **Required skills match** | 35 | Share of *required* qualifications Justin clearly meets, counting experience in his bullets, not just the skills list. All met = 35. |
| **Level fit** | 20 | New grad / SWE I / 0–1 yr, window includes June 2026 = 20 · 0–2 yrs = 17 · class-of-2027 window or "2027" in title = 15 · 1–3 yrs = 10 · 2+ yrs = 6 |
| **Preferred / domain match** | 15 | Preferred quals met + overlap with his domains: AI agents/LLM/RAG, backend APIs, distributed systems/K8s, concurrency/C++, networking/security |
| **ATS keyword coverage** | 15 | Of the JD's ~10 most important technical keywords, how many appear **literally** on the resume. A skill he has but doesn't name counts as a miss here, which is the point: it becomes a resume tweak. |
| **Location** | 10 | Seattle area = 10 · Remote US = 9 · California / New York = 8 |
| **Freshness** | 5 | Posted ≤2 days ago = 5 · 3–4 days = 3 · 5–7 days = 2 · older = 1 |

## Tiers
- **80+ Apply today** — strong match, apply within 48 hours. Target: **5–8 per day.** If fewer than 5
  score 80+, the daily run keeps reading descriptions (up to 30); if still short, it tops the list up
  with the best 75–79 jobs, clearly marked.
- **65–79 Worth a look** — good match with a gap or flag; tailor the resume first
- **50–64 Stretch** — apply only if the company is a priority
- **<50 Skip**

## Per-job output
For every scored job the daily file shows: score breakdown, matched keywords, missing keywords
(split into **"you have it, add it to the resume"** and **"true gap"**), and one concrete resume tweak
(which bullet to lead with or which term to add).
