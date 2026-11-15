#!/usr/bin/env python3
"""Render a jobde_ck 1080x1080 job poster (JPEG) from a job JSON file.

Usage:
  python3 scripts/render_poster.py job.json out.jpg [--template NN|file]
  python3 scripts/render_poster.py --which                 # show today's period + template
  python3 scripts/render_poster.py --check-template FILE   # validate a new design

5-day design rotation (from Mon 16 Nov 2026, IST):
  period 0  = everything before 16 Nov 2026          -> templates/designs/00-*.html
  period 1  = 16-20 Nov 2026, period 2 = 21-25 Nov ... -> templates/designs/NN-*.html
Every period uses a NEW design that has never been used before. If the file for
today's period does not exist yet the script exits with code 3 and prints
NEW_TEMPLATE_NEEDED: the run must create it first (see RUNBOOK.md, section 2b).

Extras added automatically (layout is unchanged):
  * tech-stack chips get an icon when the skill is known (assets/tech-icons, Devicon, MIT)
  * the hiring company's logo is shown before the company name when available
    (assets/company-logos/<slug>.svg|png|jpg|webp, else looked up by exact name in
    the Simple Icons set from npm and cached into assets/company-logos/)
  * a small role illustration (assets/role-art/*.svg) sits at the right end of the company line
    (picked from role/skills; override with "role_art" in the job JSON, or "none")
"""
import html, json, os, re, sys, glob, shutil, subprocess, tarfile, datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DESIGNS = ROOT / "templates" / "designs"
ASSETS = ROOT / "assets"
ANCHOR = datetime.date(2026, 11, 16)  # first day of period 1
PERIOD_DAYS = 5
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
OPTIONAL = ["ROLE_SLUG", "LEVEL_SLUG"]  # may appear 0 or 1 times
REQUIRED = ["ROLE", "ROLE_SIZE", "COMPANY", "COMPANY_LOGO",
            "EXPERIENCE", "EXPERIENCE_NOTE", "CITY", "LOCATION_NOTE", "SALARY_CARD",
            "FOURTH_CARD", "CHIPS", "SOURCE", "POSTED", "LOGO", "ELIGIBILITY", "ROLE_ART"]


# ---------------------------------------------------------------- periods
def period_for(day):
    if day < ANCHOR:
        return 0
    return 1 + (day - ANCHOR).days // PERIOD_DAYS


def period_range(p):
    if p == 0:
        return None, ANCHOR - datetime.timedelta(days=1)
    start = ANCHOR + datetime.timedelta(days=(p - 1) * PERIOD_DAYS)
    return start, start + datetime.timedelta(days=PERIOD_DAYS - 1)


def template_for_period(p):
    hits = sorted(DESIGNS.glob(f"{p:02d}-*.html"))
    return hits[0] if hits else None


def pick_template(override=None):
    if override:
        o = str(override)
        if o.endswith(".html"):
            return Path(o) if Path(o).exists() else DESIGNS / o
        t = template_for_period(int(o))
        if not t:
            sys.exit(f"no design for period {o}")
        return t
    p = period_for(datetime.datetime.now(IST).date())
    t = template_for_period(p)
    if not t:
        s, e = period_range(p)
        print(f"NEW_TEMPLATE_NEEDED: period {p:02d} ({s:%d %b}–{e:%d %b %Y}). Create "
              f"templates/designs/{p:02d}-<name>.html (RUNBOOK 2b), check it with "
              f"--check-template, then render again.", file=sys.stderr)
        sys.exit(3)
    return t


def check_template(path):
    s = Path(path).read_text()
    errs = []
    for k in REQUIRED:
        n = s.count("{{" + k + "}}")
        if n != 1:
            errs.append(f"{{{{{k}}}}} appears {n}x (must be exactly 1)")
    for k in OPTIONAL:
        if s.count("{{" + k + "}}") > 1:
            errs.append(f"{{{{{k}}}}} appears more than once")
    if "width:1080px;height:1080px" not in s.replace(" ", ""):
        errs.append("root div must be width:1080px;height:1080px")
    if not re.search(r'<div style="position:relative;padding-right:90px;[^"]*">[^\n]*\{\{COMPANY_LOGO\}\}[^\n]*\{\{ROLE_ART\}\}</div>', s):
        errs.append("company line must be <div style=\"position:relative;padding-right:90px;...\">{{COMPANY_LOGO}}...{{COMPANY}}...{{ROLE_ART}}</div> on one line")
    for c in [".card", ".lbl", ".val", ".note", ".chip", ".val.salary"]:
        if c + "{" not in s.replace(" {", "{"):
            errs.append(f"missing CSS rule {c}")
    used = {p.name for p in DESIGNS.glob("*.html")} - {Path(path).name}
    if Path(path).read_bytes() in {(DESIGNS / u).read_bytes() for u in used}:
        errs.append("identical to an existing design; a new period needs a new look")
    print("\n".join(errs) if errs else f"OK: {path}")
    return not errs


# ---------------------------------------------------------------- icons
ALIASES = {
    "aws": "amazonwebservices", "amazonwebservices": "amazonwebservices", "eks": "amazonwebservices",
    "gcp": "googlecloud", "googlecloud": "googlecloud", "gke": "googlecloud",
    "aks": "azure", "microsoftazure": "azure", "k8s": "kubernetes", "c#": "csharp",
    "reactjs": "react", "node.js": "nodejs", "node": "nodejs", "golang": "go",
    "kafka": "apachekafka", "airflow": "apacheairflow", "spark": "apachespark",
    "elk": "elasticsearch", "elasticstack": "elasticsearch", "gitlabci": "gitlab",
    "gitlabcicd": "gitlab", "argo": "argocd", "hashicorpvault": "vault",
    "postgres": "postgresql", "shell": "bash", "shellscripting": "bash",
    "bashscripting": "bash", "scripting": "bash", "rhel": "redhat", "otel": "opentelemetry",
    "jaeger": "jaegertracing", "github": "github", "githubenterprise": "github",
    "tf": "terraform", "gha": "githubactions", "azurepipelines": "azuredevops",
}


def _norm(s):
    return re.sub(r"[^a-z0-9#+]", "", s.lower())


def tech_icon(skill):
    icons = ASSETS / "tech-icons"
    n = _norm(skill)
    name = ALIASES.get(n, n)
    if (icons / f"{name}.svg").exists():
        return icons / f"{name}.svg"
    for tok in re.split(r"[\s/,&()+-]+", skill.lower()):
        t = ALIASES.get(_norm(tok), _norm(tok))
        if len(t) > 2 and (icons / f"{t}.svg").exists():
            return icons / f"{t}.svg"
    return None


def _simple_icons_dir():
    cache = Path.home() / ".cache" / "jobde_ck" / "simple-icons"
    if (cache / "package" / "data" / "simple-icons.json").exists():
        return cache / "package"
    try:
        cache.mkdir(parents=True, exist_ok=True)
        out = subprocess.run(["npm", "pack", "simple-icons@16.38.0", "--silent"], cwd=cache,
                             capture_output=True, text=True, timeout=120)
        tgz = cache / out.stdout.strip().splitlines()[-1]
        with tarfile.open(tgz) as t:
            t.extractall(cache, filter="data")
        tgz.unlink()
        return cache / "package"
    except Exception as ex:  # network/npm missing: just skip the logo
        print(f"company logo lookup skipped ({ex})", file=sys.stderr)
        return None


def company_logo(company):
    slug = re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")
    for ext in ("svg", "png", "jpg", "jpeg", "webp"):
        p = ASSETS / "company-logos" / f"{slug}.{ext}"
        if p.exists():
            return p
    if (ASSETS / "company-logos" / f"{slug}.none").exists():
        return None
    si = _simple_icons_dir()
    if not si:
        return None
    want = _norm(company)
    for icon in json.loads((si / "data" / "simple-icons.json").read_text()):
        names = [icon["title"]] + icon.get("aliases", {}).get("aka", [])
        if want in {_norm(n) for n in names}:
            svg = (si / "icons" / f"{icon['slug']}.svg").read_text()
            svg = svg.replace("<svg ", f'<svg fill="#{icon["hex"]}" ', 1)
            dest = ASSETS / "company-logos" / f"{slug}.svg"
            dest.write_text(svg)
            print(f"company logo: {icon['title']} (Simple Icons) -> {dest.relative_to(ROOT)}", file=sys.stderr)
            return dest
    (ASSETS / "company-logos" / f"{slug}.none").write_text("no logo found in Simple Icons\n")
    return None


ROLE_ART_RULES = [
    ("shield", r"devsecops|security|secops"),
    ("mlops", r"mlops|machine learning|\bml\b|\bai\b|llm"),
    ("stream", r"kafka|stream"),
    ("observability", r"observab|monitor|grafana|prometheus|datadog|elk"),
    ("reliability", r"\bsre\b|site reliability|reliability"),
    ("containers", r"kubernetes|k8s|platform|container|openshift"),
    ("pipeline", r"ci/cd|cicd|build|release|jenkins|pipeline"),
    ("cloud", r"cloud|aws|azure|gcp"),
    ("server", r"infra|linux|system"),
]


def role_art(job):
    choice = (job.get("role_art") or "").strip()
    if choice.lower() == "none":
        return ""
    if not choice:  # decided by the role title only; plain "DevOps" roles get the pipeline art
        role = job.get("role", "").lower()
        choice = next((n for n, rx in ROLE_ART_RULES if re.search(rx, role)), "pipeline")
    f = ASSETS / "role-art" / f"{choice}.svg"
    if not f.exists():
        return ""
    svg = f.read_text().replace("<svg ", '<svg width="76" height="76" ', 1)
    return (f'<span aria-hidden="true" style="position:absolute;right:0;top:50%;'
            f'transform:translateY(-50%);opacity:.55;line-height:0">{svg}</span>')


# ---------------------------------------------------------------- build
def card(label, value, note, cls="val"):
    return (f'<div class="card"><div class="lbl">{label}</div>'
            f'<div class="{cls}">{html.escape(value)}</div>'
            f'<div class="note">{html.escape(note)}</div></div>')


def chip(skill):
    icon = tech_icon(skill)
    if not icon:
        return f'<span class="chip">{html.escape(skill)}</span>'
    return (f'<span class="chip" style="display:inline-flex;align-items:center;gap:8px">'
            f'<span style="display:inline-flex;background:#FFFFFF;border-radius:6px;padding:2px">'
            f'<img src="{icon.as_uri()}" style="width:20px;height:20px;display:block"></span>'
            f'{html.escape(skill)}</span>')


def build(job, template):
    e = lambda k, d="": html.escape(str(job.get(k) or d))
    salary = (job.get("salary") or "").strip()
    hidden = salary == "" or salary.lower().startswith("not disclosed")
    if hidden:
        salary_card = card("JOB TYPE", job.get("employment_type") or "Full-time", job.get("work_mode") or "Apply via link")
    else:
        salary_card = card("CTC", salary, job.get("employment_type") or "Full-time", "val salary")
    fourth = card("OPENINGS", job.get("openings") or "Hiring now", job.get("openings_note") or "Apply early")
    chips = "".join(chip(s) for s in job.get("skills", [])[:9])
    role = job["role"]
    role_size = 84 if len(role) <= 22 else 70
    logos = glob.glob(str(ASSETS / "logo.*"))
    logo = (f'<img src="file://{logos[0]}" style="height:116px;width:116px;object-fit:contain;border-radius:50%;display:block">'
            if logos else "")
    cl = company_logo(job.get("company", ""))
    company_logo_html = ""
    if cl:
        pill = "#FFFFFF"
        if cl.suffix == ".svg":
            m = re.search(r'fill="#([0-9A-Fa-f]{6})"', cl.read_text())
            if m:  # light brand colour (e.g. DHL yellow) -> dark pill so it stays visible
                r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
                if 0.299 * r + 0.587 * g + 0.114 * b > 170:
                    pill = "#1B1F24"
            size = 'height:34px;width:60px' if 'viewBox="0 0 24 24"' in cl.read_text() else 'height:30px;width:auto;max-width:120px'
        else:
            size = 'height:30px;width:auto;max-width:120px'
        company_logo_html = (
            f'<span style="display:inline-flex;align-items:center;justify-content:center;background:{pill};'
            f'border-radius:10px;padding:6px 10px;margin-right:14px;vertical-align:middle">'
            f'<img src="{cl.as_uri()}" style="{size};object-fit:contain;display:block"></span>')
    out = template.read_text()
    for k, v in {
        "ROLE": html.escape(role), "ROLE_SIZE": str(role_size),
        "ROLE_SLUG": e("role_slug", "devops"), "LEVEL_SLUG": e("level_slug", "mid"),
        "COMPANY": e("company"), "COMPANY_LOGO": company_logo_html,
        "EXPERIENCE": e("experience", "See listing"),
        "EXPERIENCE_NOTE": e("experience_note"), "CITY": e("city"),
        "LOCATION_NOTE": e("location_note"), "SALARY_CARD": salary_card,
        "FOURTH_CARD": fourth, "CHIPS": chips, "SOURCE": e("source"),
        "POSTED": e("posted"), "LOGO": logo, "ROLE_ART": role_art(job),
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
    if args and args[0] == "--which":
        p = period_for(datetime.datetime.now(IST).date())
        s, e = period_range(p)
        t = template_for_period(p)
        print(f"period {p:02d} ({s:%d %b} – {e:%d %b %Y}): {t.name if t else 'NEW_TEMPLATE_NEEDED'}"
              if s else f"period 00 (until {e:%d %b %Y}): {t.name if t else 'NEW_TEMPLATE_NEEDED'}")
        sys.exit(0 if t else 3)
    if args and args[0] == "--check-template":
        sys.exit(0 if check_template(args[1]) else 1)
    ov = None
    if "--template" in args:
        i = args.index("--template"); ov = args[i + 1]; del args[i:i + 2]
    main(args[0], args[1], ov)
