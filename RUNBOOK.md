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
The JobDeck logo (`assets/logo.png`) is shown top-left on every template; the renderer auto-shrinks long role titles so nothing overflows. Don't pass `--template` in scheduled runs.

### 2a. Design rotation — a NEW design every 5 days
- Periods (IST): period 00 = up to 15 Nov 2026; period 01 = 16–20 Nov 2026; period 02 = 21–25 Nov; and so on, 5 days each (`python3 scripts/render_poster.py --which` prints today's period and design).
- Each period uses its own design file `templates/designs/NN-<name>.html` (NN = period number, 2 digits). Every period must look new — never reuse an older design.
- Already prepared: 00-terminal-dark (used), 01-paper-light, 02-gradient-glass, 03-blueprint.
- If the render exits with code 3 / prints `NEW_TEMPLATE_NEEDED`, do section 2b first, then render again.

### 2b. Making the new design (only when NEW_TEMPLATE_NEEDED)
- Copy the most recent design to `templates/designs/NN-<short-name>.html`.
- **Layout must not change**: same 1080×1080 root, same blocks in the same order and positions — header (JobDeck logo + kicker + tag pill), role title, company line, 2×2 cards (Experience, Salary/Job type, Location, Openings), tech-stack chips, Eligibility line, Apply bar at the bottom. Keep every `{{PLACEHOLDER}}` exactly once, keep the company-line `<div style="position:relative;padding-right:90px;...">{{COMPANY_LOGO}}…{{COMPANY}}…{{ROLE_ART}}</div>` and the CSS classes `.card .lbl .val .note .val.salary .chip`.
- Change only the look: colour palette, background (gradients, subtle patterns, grids, shapes drawn in CSS/inline SVG), fonts (Google Fonts only), card/chip/CTA styling, kicker/tag wording. Make it clearly different from the last 3 designs. Keep text contrast high (WCAG AA) and all text readable on a phone.
- No external images other than Google Fonts; draw any decoration in CSS or inline SVG yourself. Don't use other brands' logos as decoration.
- Validate: `python3 scripts/render_poster.py --check-template templates/designs/NN-<name>.html` must print OK. Then render the job, look at the JPEG, fix anything that overflows or looks off.
- Commit the new design together with the job's poster.

### 2c. Logos and images (automatic — layout unchanged)
- **Tech-stack icons**: a chip gets a small icon when its skill matches a file in `assets/tech-icons/` (Devicon set, MIT; aliases like AWS, GCP, K8s, Kafka are handled in the script). To add a tool, copy its icon from the Devicon npm package (`npm pack devicon`) into `assets/tech-icons/<name>.svg`. Write skills with their usual names (e.g. "Terraform", "GitHub Actions") so they match.
- **Hiring company logo**: shown in a small pill before the company name when `assets/company-logos/<company-slug>.svg|png|jpg|webp` exists; otherwise the script looks up the exact company name in the Simple Icons set (npm) and caches it there. If none is found it writes `<slug>.none` and shows no logo — never draw or invent a company logo. You may add a real logo file taken from the company's own official website/press kit if you can reach it; otherwise skip.
- **Role illustration**: a small line-art icon at the right end of the company line, chosen from the role title (`assets/role-art/`: cloud, pipeline, containers, server, reliability, shield, observability, stream, mlops). Override with `"role_art": "<name>"` or `"none"` in the job JSON.
- Commit any new files under `assets/` with the poster.

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
