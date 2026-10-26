# Resume review — what a recruiter and an ATS will notice

One-time review of `Justin_Resume.pdf` (Oct 2026). Daily files add job-specific tweaks on top of this.

## Fix first (screening blockers)
1. **Add your graduation date.** Education reads "B.S Computer Science" with no date. New-grad screens
   filter on graduation date, and with no date you can be auto-rejected or assumed to still be a student.
   → `B.S. Computer Science, June 2026 | Major GPA: 3.73`
2. **CVE is spelled out wrong.** CVE stands for *Common Vulnerabilities and Exposures*, not "common vulnerability
   exploits." A security-minded interviewer will catch it.
3. **Schrödinger project calls itself a "CI/CD pipeline."** If it's a distributed compute pipeline, say that; if it
   also had CI/CD (e.g., GitHub Actions building and deploying images), name that specifically. Mislabeling invites a
   tough interview question.

## Skills section: move what's buried in your bullets into the list
ATS keyword matching leans heavily on the skills section. These are proven in your bullets but missing from it:

| Add | Evidence on your resume |
|---|---|
| Node.js, Nest.js | Digital Omni API layer |
| SQL, Redis, NoSQL | MySQL; Redis Pub/Sub |
| CI/CD, Prometheus, Grafana, AWS EKS | Schrödinger project |
| WebSockets, Multithreading / Concurrency | Poker server |
| JWT, RBAC | Digital Omni auth |
| PyShark, Wireshark, 802.11 networking | Research |
| LLM evaluation (LLM-as-judge), ReAct agents | Network security agent |

Suggested layout:
- **Languages:** Python, Java, TypeScript, JavaScript, C++, C, SQL
- **AI & ML:** LangGraph, Claude API, RAG, ChromaDB, MCP, ReAct agents, LLM evals, LSTM (+ PyTorch/TensorFlow if that's what you used)
- **Backend & Infra:** Node.js, Nest.js, REST APIs, WebSockets, MySQL, Redis, Docker, Kubernetes (EKS), AWS, CI/CD, Prometheus, Grafana, Linux
- **Tools:** Git, Jira, Agile, Claude Code (agents.md, skills)

"agents.md, skills.md" on their own read as file names to a recruiter; folding them under "Claude Code" makes the point
(you use AI-assisted development tooling) that Amazon and others now screen for.

## Probably true but not on the page (confirm, then add)
- **PyTorch or TensorFlow:** the LSTM was built with something. Most AI/ML postings name a framework.
- **TCP/IP sockets, HTTP:** you implemented RFC 6455 from scratch, which requires both.
- **Testing:** pytest/Jest at Digital Omni? "Testing" appears in a lot of entry-level JDs.
- **Specific AWS services** (EC2, S3, IAM, RDS) beyond EKS.
- **GitHub Actions**, if used for any of the CI.

## Bullet polish
- "with a 92% accuracy" → "with 92% accuracy"
- "Implemented a LLM-as-judge" → "an LLM-as-judge"
- "chaining retrieval, and report generation" → "chaining retrieval and report generation"
- Add a metric to the AI Network Security Agent (classification accuracy from your eval harness) and to the Poker
  Server (concurrent players, latency). Those are your two strongest AI/systems projects and the only ones without numbers.
- Your research end date (June 2026) quietly confirms graduation, but recruiters spend ~7 seconds per resume, so
  put the date in Education.
