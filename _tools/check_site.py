#!/usr/bin/env python3
"""Pre-deploy checks for the static site. Standard library only.

Run from anywhere:  python3 _tools/check_site.py
Exit code 0 means every check passed; 1 means at least one problem was printed.

What it checks (each one has bitten this site before):
  1. Internal links: every href/src/srcset on a published page, every sitemap
     <loc> and every manifest icon must point at a file that exists. Same-site
     links that carry a #fragment must land on an element with that id.
  2. Structured data: every <script type="application/ld+json"> block must
     parse, every schema.org Offer, AggregateOffer and price specification
     price must be a current plan price, and FAQPage question names must not
     carry the accordion's toggle arrow.
  3. Retired facts: old prices and old guarantee wording must not reappear in
     any published page, text, data, Markdown or script file.
     When a price changes, add the OLD value to RETIRED below in the same PR.
  4. Demo forms: the English and Spanish demo forms must send the same field
     names and lead-volume options. When the demo Worker (_demo-api/worker.mjs)
     is present, every field must also be on its allowlist, or it would reject
     every submission.

This folder starts with an underscore, so the GitHub Pages (Jekyll) build does
not publish it.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

SITE_HOSTS = {"aisalespipeline.com", "www.aisalespipeline.com"}

# The only monthly plan prices. Update together with pricing.html.
PLAN_PRICES = {"397", "695", "995"}
# (page, schema @type that holds the Offer, price) combinations that are not plan prices on purpose.
OFFER_EXCEPTIONS = {("simulation.html", "WebApplication", "0")}

# Retired values. Each entry is (regex, why). Matching is case-insensitive and
# runs over every published file with a RETIRED_SUFFIXES extension.
RETIRED = [
    (r"\$999(?![\d,])", "old $999 setup fee (now $2,499 KW / $4,000 non-KW)"),
    (r"\$497(?![\d,])", "old $497 Basic price (now $397)"),
    (r"\$8,673", "old Pro annual cost (pricing.html shows $9,173 KW / $9,673 non-KW)"),
    (r"\$58,827", "old ISA savings figure (pricing.html shows $58,327 KW / $57,827 non-KW)"),
    (r"\$8,340-\$11,940", "old annual range that left out Basic and the setup fee"),
    (r"\$495-", "plan range that never existed (plans are $397/$695/$995)"),
    (r"\$1,995", "plan price that never existed (plans are $397/$695/$995)"),
    (r"12[-\u2013]18%", "old ISA cost ratio from the $999 setup fee (Pro and Elite are now roughly 14-20%)"),
    (r"\$6,000-\$?12,000", "old annual range (plans are $4,764-$11,940 a year plus the setup fee)"),
    (r"free trial available", "there is no free trial (see the pricing FAQ)"),
    (r"refund[^<.]{0,80}\.\s*no questions", "the guarantee is conditional (terms.html), not 'no questions asked'"),
]
RETIRED_SUFFIXES = (".html", ".txt", ".json", ".xml", ".md", ".js")

# schema.org types that carry a price, and the properties that hold it.
PRICED_TYPES = {"Offer", "AggregateOffer"}
PRICE_KEYS = ("price", "lowPrice", "highPrice", "minPrice", "maxPrice")
# Accordion toggle glyphs that must not leak into FAQPage question names.
TOGGLE_GLYPHS = "\u25bc\u25b2\u25be\u25b4\u25b6\u25ba"

# FormSubmit settings that the demo-protection activation script strips out.
FORM_CONFIG_FIELDS = {"_subject", "_template", "_next", "_captcha", "_autoresponse"}
DEMO_FORMS = ("index.html", "es/index.html")

SKIP_SCHEMES = ("mailto:", "tel:", "sms:", "javascript:", "data:", "blob:")


def published_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    """Files GitHub Pages serves: skips _folders, .folders and git internals."""
    out = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part.startswith(("_", ".")) for part in rel.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            out.append(path)
    return out


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[tuple[int, str]] = []
        self.ids: set[str] = set()
        self.ld_blocks: list[tuple[int, str]] = []
        self._in_ld: int | None = None
        self._ld_buf: list[str] = []
        # Demo form tracking.
        self.forms: list[dict] = []
        self._form: dict | None = None
        self._select: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        line = self.getpos()[0]
        for key in ("id", "name") if tag == "a" else ("id",):
            if a.get(key):
                self.ids.add(a[key])
        for key in ("href", "src"):
            if a.get(key):
                self.refs.append((line, a[key]))
        if a.get("srcset"):
            for candidate in a["srcset"].split(","):
                url = candidate.strip().split(" ")[0]
                if url:
                    self.refs.append((line, url))
        if tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in_ld = line
            self._ld_buf = []
        if tag == "form":
            self._form = {"line": line, "action": a.get("action", ""), "fields": [], "options": {}}
            self.forms.append(self._form)
        if self._form is not None:
            if tag in ("input", "select", "textarea") and a.get("name"):
                self._form["fields"].append(a["name"])
            if tag == "select":
                self._select = a.get("name")
                self._form["options"].setdefault(self._select, [])
            if tag == "option" and self._select:
                self._form["options"][self._select].append(a.get("value", ""))

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld is not None:
            self.ld_blocks.append((self._in_ld, "".join(self._ld_buf)))
            self._in_ld = None
        if tag == "select":
            self._select = None
        if tag == "form":
            self._form = None

    def handle_data(self, data):
        if self._in_ld is not None:
            self._ld_buf.append(data)


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    parser.close()
    return parser


def resolve(root: Path, page: Path, url: str) -> tuple[Path | None, str]:
    """Map a reference to (file on disk or None if external, fragment)."""
    url = url.strip()
    if not url or url.startswith(SKIP_SCHEMES):
        return None, ""
    parts = urlsplit(url)
    if parts.scheme in ("http", "https") or url.startswith("//"):
        if (parts.hostname or "").lower() not in SITE_HOSTS:
            return None, ""
        path = parts.path or "/"
    elif parts.scheme:
        return None, ""
    else:
        path = parts.path
    fragment = unquote(parts.fragment)
    if not path:  # "#section" on the same page
        return page, fragment
    path = unquote(path)
    if path.startswith("/"):
        target = root / path.lstrip("/")
    else:
        target = page.parent / path
    if path.endswith("/"):
        target = target / "index.html"
    elif not target.is_file() and Path(f"{target}.html").is_file():
        # GitHub Pages serves /page from page.html, even when a page/ folder also exists.
        target = Path(f"{target}.html")
    elif target.is_dir():
        target = target / "index.html"
    return target, fragment


def is_priced(types) -> bool:
    return any(t in PRICED_TYPES or str(t).endswith("PriceSpecification") for t in types)


def offers(node, holder_type=None):
    """Yield (holder @type, priced node) for every Offer, AggregateOffer and
    price specification in a JSON-LD tree. The holder is the nearest enclosing
    type that is not itself priced (for example SoftwareApplication), so a
    price specification inside an Offer reports the same holder as its Offer."""
    if isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        priced = is_priced(types)
        if priced:
            yield holder_type, node
        own = holder_type if priced or not isinstance(t, str) else t
        for value in node.values():
            yield from offers(value, own)
    elif isinstance(node, list):
        for value in node:
            yield from offers(value, holder_type)


def prices(node: dict) -> list[str]:
    """Every price value on a priced node. An Offer must have a price, so a
    missing one is returned as '' and reported."""
    found = [str(node[k]).strip() for k in PRICE_KEYS if k in node]
    types = node.get("@type")
    types = types if isinstance(types, list) else [types]
    if not found and "Offer" in types:
        found = [""]
    return found


def faq_questions(node):
    """Yield the name of every Question inside a FAQPage in a JSON-LD tree."""
    if isinstance(node, dict):
        t = node.get("@type")
        types = t if isinstance(t, list) else [t]
        if "FAQPage" in types:
            for item in node.get("mainEntity") or []:
                if isinstance(item, dict):
                    yield str(item.get("name", ""))
        for value in node.values():
            yield from faq_questions(value)
    elif isinstance(node, list):
        for value in node:
            yield from faq_questions(value)


def worker_contract(root: Path):
    """(allowed field names, allowed leads_per_month values) from the demo Worker, if present."""
    worker = root / "_demo-api" / "worker.mjs"
    if not worker.exists():
        return None
    source = worker.read_text(encoding="utf-8")
    fields = re.search(r"const FIELDS = new Set\(\[([^\]]*)\]\)", source)
    volumes = re.search(r"if \(!\[([^\]]*)\]\.includes\(lead\.leads_per_month\)", source)
    if not fields:
        return "could not find `const FIELDS = new Set([...])` in _demo-api/worker.mjs"
    if not volumes:
        return ("could not find the leads_per_month allowlist "
                "(`if (![...].includes(lead.leads_per_month)`) in _demo-api/worker.mjs; "
                "update worker_contract() in _tools/check_site.py to match the Worker")
    allowed = set(re.findall(r"'([^']*)'", fields.group(1)))
    allowed_volumes = set(re.findall(r"'([^']*)'", volumes.group(1)))
    return allowed, allowed_volumes


def check(root: Path) -> list[str]:
    root = root.resolve()
    problems: list[str] = []
    html_files = published_files(root, (".html",))
    parsed = {p: parse_page(p) for p in html_files}

    def rel(p: Path) -> str:
        return p.relative_to(root).as_posix()

    def ids_of(target: Path) -> set[str]:
        if target not in parsed:
            parsed[target] = parse_page(target)
        return parsed[target].ids

    # 1. Links and anchors.
    for page, info in parsed.items():
        if page not in html_files:
            continue
        for line, url in info.refs:
            target, fragment = resolve(root, page, url)
            if target is None:
                continue
            if not target.exists():
                problems.append(f"{rel(page)}:{line}: broken link {url!r}")
            elif fragment and target.suffix == ".html" and fragment not in ids_of(target):
                problems.append(f"{rel(page)}:{line}: {url!r} has no element with id={fragment!r}")

    sitemap = root / "sitemap.xml"
    if sitemap.exists():
        for loc in re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sitemap.read_text(encoding="utf-8")):
            target, _ = resolve(root, sitemap, loc)
            if target is not None and not target.exists():
                problems.append(f"sitemap.xml: <loc> {loc} has no file")

    manifest = root / "manifest.json"
    if manifest.exists():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except ValueError as exc:
            problems.append(f"manifest.json: invalid JSON ({exc})")
        else:
            for icon in data.get("icons", []):
                target, _ = resolve(root, manifest, icon.get("src", ""))
                src = icon.get("src")
                if target is None:
                    continue
                if not target.exists():
                    problems.append(f"manifest.json: icon {src!r} has no file")
                    continue
                size = png_size(target)
                if icon.get("type") == "image/png" and size is None:
                    problems.append(f"manifest.json: icon {src!r} is declared image/png but is not a PNG file")
                    continue
                declared = {s for s in icon.get("sizes", "").split() if s != "any"}
                if size and declared and f"{size[0]}x{size[1]}" not in declared:
                    problems.append(f"manifest.json: icon {src!r} is {size[0]}x{size[1]} but declares {icon.get('sizes')!r}")

    # 2. Structured data.
    for page in html_files:
        for line, block in parsed[page].ld_blocks:
            try:
                data = json.loads(block)
            except ValueError as exc:
                problems.append(f"{rel(page)}:{line}: JSON-LD does not parse ({exc})")
                continue
            for holder, offer in offers(data):
                kind = offer.get("@type")
                for price in prices(offer):
                    if price in PLAN_PRICES or (rel(page), holder, price) in OFFER_EXCEPTIONS:
                        continue
                    problems.append(
                        f"{rel(page)}:{line}: {holder} {kind} price {price!r} is not a plan price ({', '.join(sorted(PLAN_PRICES))})"
                    )
            for name in faq_questions(data):
                if any(glyph in name for glyph in TOGGLE_GLYPHS):
                    problems.append(f"{rel(page)}:{line}: FAQPage question {name!r} contains a toggle arrow")

    # 3. Retired facts.
    patterns = [(re.compile(rx, re.IGNORECASE), why) for rx, why in RETIRED]
    for path in published_files(root, RETIRED_SUFFIXES):
        for number, text in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for rx, why in patterns:
                if rx.search(text):
                    problems.append(f"{rel(path)}:{number}: retired value ({why})")

    # 4. Demo forms stay in sync with each other and with the Worker allowlist.
    demo = {}
    for name in DEMO_FORMS:
        page = root / name
        if page not in parsed:
            problems.append(f"{name}: demo form page is missing")
            continue
        forms = parsed[page].forms
        if len(forms) != 1:
            problems.append(f"{name}: expected exactly one demo <form>, found {len(forms)}")
            continue
        demo[name] = forms[0]
    if len(demo) == len(DEMO_FORMS):
        names = {n: set(f["fields"]) - FORM_CONFIG_FIELDS for n, f in demo.items()}
        volumes = {n: f["options"].get("leads_per_month", []) for n, f in demo.items()}
        first, second = DEMO_FORMS
        if names[first] != names[second]:
            problems.append(
                f"demo forms send different fields: only in {first}: {sorted(names[first] - names[second])}, "
                f"only in {second}: {sorted(names[second] - names[first])}"
            )
        if volumes[first] != volumes[second]:
            problems.append(f"demo forms have different leads_per_month options: {volumes[first]} vs {volumes[second]}")
        contract = worker_contract(root)
        if isinstance(contract, str):
            problems.append(contract)
        elif contract:
            allowed, allowed_volumes = contract
            for n in DEMO_FORMS:
                extra = names[n] - allowed
                if extra:
                    problems.append(f"{n}: fields {sorted(extra)} are not in the Worker FIELDS allowlist; it would reject every submission")
                missing = {v for v in volumes[n] if v} - allowed_volumes
                if missing:
                    problems.append(f"{n}: leads_per_month options {sorted(missing)} would be rejected by the Worker")
    return problems


def png_size(path: Path):
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = check(root)
    for problem in problems:
        print(problem)
    pages = len(published_files(root.resolve(), (".html",)))
    if problems:
        print(f"\n{len(problems)} problem(s) across {pages} pages.")
        return 1
    print(f"All checks passed for {pages} pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
