#!/usr/bin/env python3
"""Render a jobde_ck 1080x1080 job poster (JPEG) from a job JSON file.

Usage: python3 scripts/render_poster.py job.json out.jpg [--template N]

Weekly template rotation: templates/weekly/*.html (sorted by name) are used one
per week (Monday-Sunday, IST). The week of Mon 9 Nov 2026 uses template 1, the
next week template 2, and so on, wrapping around. Override with --template N
(1-based) or env POSTER_TEMPLATE=N.
Job JSON keys: role, role_slug, level_slug, company, experience, experience_note,
salary (empty / "Not disclosed" => salary card hidden), employment_type, city,
location_note, openings, openings_note, skills (list), source, posted.
"""
import html, json, os, sys, glob, datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = sorted((ROOT / "templates" / "weekly").glob("*.html"))
ANCHOR_MONDAY = datetime.date(2026, 11, 9)  # week using template 1
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def pick_template(override=None):
    if override:
        return TEMPLATES[(int(override) - 1) % len(TEMPLATES)]
    today = datetime.datetime.now(IST).date()
    weeks = (today - ANCHOR_MONDAY).days // 7
    return TEMPLATES[weeks % len(TEMPLATES)]
LOGO_GLOB = str(ROOT / "assets" / "logo.*")


def card(label, value, note, cls="val"):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="{cls}">{html.escape(value)}</div>'
            f'<div class="note">{html.escape(note)}</div></div>')


def build(job, template):
    e = lambda k, d="": html.escape(str(job.get(k) or d))
    salary = (job.get("salary") or "").strip()
    hidden = salary == "" or salary.lower().startswith("not disclosed")
    if hidden:
        salary_card = card("JOB TYPE", job.get("employment_type") or "Full-time", job.get("work_mode") or "Apply via link")
    else:
        salary_card = card("CTC", salary, job.get("employment_type") or "Full-time", "val salary")
    fourth = card("OPENINGS", job.get("openings") or "Hiring now", job.get("openings_note") or "Apply early")
    chips = "".join(f'<span class="chip">{html.escape(s)}</span>' for s in job.get("skills", [])[:9])
    role = job["role"]
    role_size = 84 if len(role) <= 22 else 70
    logos = glob.glob(LOGO_GLOB)
    logo = (f'<img src="file://{logos[0]}" style="height:116px;width:116px;object-fit:contain;border-radius:50%;display:block">'
            if logos else "")
    out = template.read_text()
    for k, v in {
        "ROLE": html.escape(role), "ROLE_SIZE": str(role_size),
        "ROLE_SLUG": e("role_slug", "devops"), "LEVEL_SLUG": e("level_slug", "mid"),
        "COMPANY": e("company"), "EXPERIENCE": e("experience", "See listing"),
        "EXPERIENCE_NOTE": e("experience_note"), "CITY": e("city"),
        "LOCATION_NOTE": e("location_note"), "SALARY_CARD": salary_card,
        "FOURTH_CARD": fourth, "CHIPS": chips, "SOURCE": e("source"),
        "POSTED": e("posted"), "LOGO": logo,
        "ELIGIBILITY": e("eligibility", "See the full listing for requirements."),
    }.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def main(job_path, out_path, override=None):
    job = json.loads(Path(job_path).read_text())
    template = pick_template(override or os.environ.get("POSTER_TEMPLATE"))
    print(f"template: {template.name}", file=sys.stderr)
    tmp = Path(out_path).with_suffix(".html")
    tmp.write_text(build(job, template))
    exe = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(1500)
        # Auto-fit: shrink the role title until the card fits in 1080px.
        pg.evaluate("""() => {
          const root = document.body.firstElementChild, h1 = root.querySelector('h1');
          let size = parseFloat(getComputedStyle(h1).fontSize);
          while (root.scrollHeight > 1080 && size > 50) { size -= 4; h1.style.fontSize = size + 'px'; }
        }""")
        if pg.evaluate("document.body.firstElementChild.scrollHeight") > 1080:
            print("WARNING: poster still overflows; shorten eligibility/skills", file=sys.stderr)
        pg.screenshot(path=out_path, type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        b.close()
    tmp.unlink()
    print(out_path)


if __name__ == "__main__":
    args = sys.argv[1:]
    ov = None
    if "--template" in args:
        i = args.index("--template"); ov = args[i + 1]; del args[i:i + 2]
    main(args[0], args[1], ov)
