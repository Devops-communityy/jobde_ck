#!/usr/bin/env python3
"""Render a jobde_ck 1080x1080 job poster (JPEG) from a job JSON file.

Usage: python3 scripts/render_poster.py job.json out.jpg
Job JSON keys: role, role_slug, level_slug, company, experience, experience_note,
salary (empty / "Not disclosed" => salary card hidden), employment_type, city,
location_note, openings, openings_note, skills (list), source, posted.
"""
import html, json, os, sys, glob
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "poster-1x1.html"
LOGO_GLOB = str(ROOT / "assets" / "logo.*")


def card(label, value, note, color="#FFFFFF"):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="val" style="color:{color}">{html.escape(value)}</div>'
            f'<div class="note">{html.escape(note)}</div></div>')


def build(job):
    e = lambda k, d="": html.escape(str(job.get(k) or d))
    salary = (job.get("salary") or "").strip()
    hidden = salary == "" or salary.lower().startswith("not disclosed")
    if hidden:
        salary_card = card("JOB TYPE", job.get("employment_type") or "Full-time", job.get("work_mode") or "Apply via link")
    else:
        salary_card = card("CTC", salary, job.get("employment_type") or "Full-time", "#F5B83D")
    fourth = card("OPENINGS", job.get("openings") or "Hiring now", job.get("openings_note") or "Apply early")
    chips = "".join(f'<span class="chip">{html.escape(s)}</span>' for s in job.get("skills", [])[:9])
    role = job["role"]
    role_size = 84 if len(role) <= 22 else 70
    logos = glob.glob(LOGO_GLOB)
    logo = (f'<img src="file://{logos[0]}" style="height:56px;width:56px;object-fit:contain;border-radius:12px">'
            if logos else "")
    out = TEMPLATE.read_text()
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


def main(job_path, out_path):
    job = json.loads(Path(job_path).read_text())
    tmp = Path(out_path).with_suffix(".html")
    tmp.write_text(build(job))
    exe = "/usr/bin/google-chrome" if os.path.exists("/usr/bin/google-chrome") else None
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1080, "height": 1080})
        pg.goto(tmp.resolve().as_uri())
        pg.wait_for_timeout(1500)
        pg.screenshot(path=out_path, type="jpeg", quality=92, clip={"x": 0, "y": 0, "width": 1080, "height": 1080})
        b.close()
    tmp.unlink()
    print(out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
