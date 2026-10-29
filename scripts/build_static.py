"""Render editable public JSON/templates to docs/ for GitHub Pages. No Flask or database."""
import copy
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "docs"


def safe_url(value):
    value = (value or "").strip()
    return value if re.match(r"^(https?://|mailto:|tel:|#|/)", value, re.I) and not value.startswith("//") else ""


def main():
    content = json.loads((SITE / "content.json").read_text(encoding="utf-8"))
    config = json.loads((SITE / "config.json").read_text(encoding="utf-8"))
    endpoint = config.get("contactEndpoint", "").strip()
    if endpoint and not re.fullmatch(r"https://formspree\.io/f/[A-Za-z0-9]+", endpoint):
        raise SystemExit("contactEndpoint must be a Formspree URL: https://formspree.io/f/FORM_ID")
    site_url = config.get("siteUrl", "").rstrip("/")
    if site_url and urlparse(site_url).scheme != "https":
        raise SystemExit("siteUrl must use HTTPS.")
    env = Environment(loader=FileSystemLoader(str(SITE / "templates")),
                      autoescape=select_autoescape(["html"]), undefined=StrictUndefined)
    # Reconcile removed products/assets without deleting outside this fixed output folder.
    OUT.mkdir(exist_ok=True)
    for path in OUT.glob("p/*/index.html"):
        path.unlink()
    if (OUT / "assets").exists():
        if (OUT / "assets").is_symlink() or (OUT / "assets").resolve().parent != OUT.resolve():
            raise SystemExit("Refusing to remove assets outside docs/.")
        shutil.rmtree(str(OUT / "assets"))
    shutil.copytree(str(SITE / "assets"), str(OUT / "assets"))
    public_config = {"contactEndpoint": endpoint}
    (OUT / "assets/config.js").write_text("window.CCF_CONFIG = " + json.dumps(public_config) + ";\n", encoding="utf-8")

    def render(template, destination, depth, index=None):
        prefix = "../" * depth
        home = prefix + "index.html"

        def asset(name):
            path = OUT / "assets" / name
            if not path.is_file() or (OUT / "assets").resolve() not in path.resolve().parents:
                raise ValueError("Missing or invalid asset: " + name)
            return prefix + "assets/" + name

        env.filters["img"] = lambda name: asset("uploads/" + name) if name else ""
        c = copy.deepcopy(content)
        for i, p in enumerate(c["products"], 1):
            p.update(i=i, href=prefix + "p/{}/index.html".format(i), ext=safe_url(p.get("link")),
                     tag_list=[s.strip() for s in re.split(r"[,，、]", p.get("tags", "")) if s.strip()],
                     fit_list=[s.strip() for s in p.get("fit", "").splitlines() if s.strip()])
            p["feature_list"] = []
            for line in p.get("features", "").splitlines():
                if line.strip():
                    title, _, text = line.partition("｜") if "｜" in line else line.partition("|")
                    p["feature_list"].append({"title": title.strip(), "text": text.strip()})
        c["custom"]["items"] = [s.strip() for s in c["custom"].get("list", "").splitlines() if s.strip()]
        c["trial"]["step_list"] = [s.strip() for s in c["trial"].get("steps", "").splitlines() if s.strip()]
        s = c["settings"]
        s["line_href"] = safe_url(s.get("line_url"))
        og_image = site_url + "/assets/uploads/" + s["og_image"] if site_url and s.get("og_image") else ""
        context = dict(C=c, S=s, s=s, LINE=s["line_href"],
                       LINE_QR=asset("uploads/" + s["line_qr"]) if s.get("line_qr") else asset("line_qr.jpg"),
                       now_year=datetime.now(timezone(timedelta(hours=8))).year,
                       home=home, asset=asset, og_image=og_image, T=c["trial"], faq=c["faq"])
        if index is not None:
            selected = c["products"][index - 1]
            trial = {**c["trial"], **selected.get("trial", {})}
            trial["step_list"] = [s.strip() for s in trial.get("steps", "").splitlines() if s.strip()]
            context.update(p=selected, T=trial, others=[p for p in c["products"] if p["i"] != index])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(env.get_template(template).render(**context) + "\n", encoding="utf-8")

    render("index.html", OUT / "index.html", 0)
    for i in range(1, len(content["products"]) + 1):
        render("product.html", OUT / "p" / str(i) / "index.html", 2, i)
    (OUT / ".nojekyll").touch()
    (OUT / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    print("Built docs/: homepage + {} product pages.".format(len(content["products"])))
    if not endpoint:
        print("Formspree endpoint is not configured. Form shows a truthful error until configured.")


if __name__ == "__main__":
    main()
