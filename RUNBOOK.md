# jobde_ck auto-post runbook (one job per run → Instagram + Threads)

Each scheduled run posts exactly ONE fresh job. Nobody is watching: don't ask questions, make sensible choices, finish.

## 0. Setup
- Repo: `Devops-communityy/jobde_ck` (public). Clone it (attach with push access first if the session doesn't have it), work inside it.
- Before anything else, `git pull`. Read `posted-jobs.md` — never repost a job already listed (match apply URL, or company + role in the last 45 days).

## 1. Find ONE job
Role family (any of): DevOps, SRE / Site Reliability, Platform Engineer, Cloud Engineer / Cloud DevOps (AWS, Azure, GCP), Kubernetes / Container platform, Infrastructure / Infra-automation, CI/CD / Build & Release (Jenkins, GitHub Actions, GitLab), Observability (Grafana, Prometheus, ELK), Kafka / streaming platform ops, DevSecOps, MLOps platform.

Experience: minimum required experience must be **3 years or more**. Prefer roles asking 3+ / 4+ / 3–6 / 4–8 years. Skip fresher / 0–2 year roles. Lead/manager roles (7+ yrs) only if nothing in the 3–6 band is available.

Location: India (any city) or Remote-India.

Freshness: posted within the last 48 hours, with a visible age/date on the page (e.g. "5h ago", "1 day ago", or a date). Never guess freshness.

Sources (anything works — use what's freshest):
- JoinDevOps city/category pages, e.g. `https://jobs.joindevops.com/jobs/in-bengaluru-karnataka-india` (also Hyderabad, Pune, Chennai, Gurugram, Noida, Mumbai; and `/jobs/devops-lead`, `/jobs/aws-devops-engineer`, `/jobs/senior-devops-engineer`). Fetches reliably and shows ages.
- Built In India: `builtin.com/jobs/as/india/...`, `builtinbengaluru.in`, `builtinpune.in`, `builtinhyderabad.in`, `builtinchennai.in` search pages.
- Company careers pages (Workday, Greenhouse, Lever, etc.).
- The Job Hunt Copilot plugin's find-jobs approach (LinkedIn, Hirist, Indeed, Instahyre, Workday via web search). Do NOT fetch Naukri job pages directly (robots.txt); never log in to any site.
- Prefer variety across posts (different companies/cities/clouds), and prefer product companies/GCCs over staffing agencies. Never post an agency post that hides the real employer.

Fetch the job page and confirm: title, company, location, experience, skills, apply URL. Never invent details. Use the listing URL you actually opened as the apply link.

## 2. Make the poster
Write `jobs/<YYYY-MM-DD>_<company-slug>_<role-slug>.json` (see existing files for the keys):
`role` (≤ 30 chars, shorten sensibly), `role_slug`, `level_slug`, `company`, `experience` (e.g. "4–8 Years"), `experience_note`, `salary` (exact text if shown, else "Not disclosed" → card auto-switches to Job type), `employment_type`, `work_mode`, `city` (≤ 14 chars), `location_note` (Hybrid/Remote/WFO or extra cities), `openings`, `openings_note`, `skills` (6–9 short chips), `eligibility` (≤ 150 chars), `source`, `posted` (e.g. "11 Nov 2026"), `apply_url`.

Render: `python3 scripts/render_poster.py jobs/<file>.json posters/<same-name>.jpg`
(needs Python Playwright; uses /usr/bin/google-chrome if present, else `python3 -m playwright install chromium`).
Open the JPEG and check nothing overflows or is cut off; shorten text and re-render if needed.
The JobDeck logo (`assets/logo.png`) is shown top-left on every template; the renderer auto-shrinks long role titles so nothing overflows. Templates rotate WEEKLY (Mon–Sun, IST): `templates/weekly/1-terminal-dark.html` → `2-paper-light.html` → `3-gradient-glass.html` → `4-blueprint.html` → back to 1. The week of Mon 9 Nov 2026 is template 1. `render_poster.py` picks the week's template automatically — don't pass `--template` in scheduled runs and don't change the designs. To add a design, drop a new `N-name.html` with the same `{{PLACEHOLDERS}}` into `templates/weekly/`.

Commit + push the JSON and JPEG to `main`. Confirm the image URL returns 200:
`https://raw.githubusercontent.com/Devops-communityy/jobde_ck/main/posters/<file>.jpg`

## 3. Post (Windsor.ai)
Instagram: connector `instagram`, account `17841414093079899` (jobde_ck), action `create_image_post`, params `image_url`, `caption`:
```
🚀 We're Hiring: <Role>
🏢 <Company>
📍 <City> · <work mode / other cities>
💼 <Experience>
💰 <Salary>            ← only if disclosed
🛠 <5–7 skills, · separated>

🔗 Apply here: <apply URL>
🤝 In collab with @devops__community
🔔 Follow @jobde_ck for daily DevOps jobs

#DevOpsJobs #<RoleTag> #<City>Jobs #<Cloud> #Kubernetes #DevOps #Hiring #SRE #CloudJobs
```
Threads: connector `threads`, account `29650479181305162`, action `create_image_post`, params `image_url`, `text` (≤ 500 chars): same lines, shorter skills, full `https://` apply URL, the line `🤝 In collab with @devops__community` just above 2 hashtags.

Windsor's Instagram/Threads actions have no collaborator-invite option, so @devops__community is credited by @mention in both posts.

Post to both. If one fails, still post to the other, then report the failure.

## 4. Log
Append to `posted-jobs.md`:
`- <YYYY-MM-DD HH:MM IST> | <Company> | <Role (City)> | <apply URL> | <IG media id> | <Threads media id>`
Commit + push.

## If nothing qualifies
If no fresh (≤ 48 h) job with 3+ years is found after checking several sources, widen to ≤ 72 h. If still nothing, post nothing and say so in the run summary.
