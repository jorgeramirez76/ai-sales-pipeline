"""Tests for check_site.py. Run: python3 -m unittest discover -s _tools"""
import tempfile
import unittest
from pathlib import Path

from check_site import check

FORM_EN = """<form action="https://formsubmit.co/x" method="POST">
<input type="hidden" name="_next" value="/thanks.html">
<input name="first_name"><input name="email">
<select name="leads_per_month"><option value="">Pick</option><option value="1-25">1-25</option></select>
<input type="text" name="_honey">
</form>"""
FORM_ES = FORM_EN.replace("/thanks.html", "/es/gracias.html")


def page(body="", head=""):
    return f"<!DOCTYPE html><html><head>{head}</head><body>{body}</body></html>"


class CheckSiteTest(unittest.TestCase):
    def site(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        base = {
            "index.html": page('<section id="contact">' + FORM_EN + "</section>"),
            "es/index.html": page('<section id="contact">' + FORM_ES + "</section>"),
        }
        base.update(files)
        for name, text in base.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return check(root)

    def test_clean_site_passes(self):
        self.assertEqual(self.site({}), [])

    def test_relative_image_under_subfolder_is_broken(self):
        problems = self.site({
            "images/a.png": "x",
            "es/page.html": page('<img src="images/a.png"><img src="/images/a.png">'),
        })
        self.assertEqual(len(problems), 1)
        self.assertIn("es/page.html", problems[0])
        self.assertIn("'images/a.png'", problems[0])

    def test_extensionless_link_resolves_like_github_pages(self):
        problems = self.site({
            "features.html": page(),
            "features/x.html": page(),
            "a.html": page('<a href="/features">ok</a><a href="/features/">missing index</a>'),
        })
        self.assertEqual(len(problems), 1)
        self.assertIn("'/features/'", problems[0])

    def test_missing_anchor_is_reported(self):
        problems = self.site({"a.html": page('<a href="/#contact">ok</a><a href="/#nope">bad</a>')})
        self.assertEqual(len(problems), 1)
        self.assertIn("id='nope'", problems[0])

    def test_offer_price_must_be_a_plan_price(self):
        ld = '<script type="application/ld+json">{"@type": "SoftwareApplication", "offers": {"@type": "Offer", "price": "%s"}}</script>'
        problems = self.site({"good.html": page(head=ld % "695"), "bad.html": page(head=ld % "0")})
        self.assertEqual(len(problems), 1)
        self.assertIn("bad.html", problems[0])

    def test_aggregate_offer_and_price_specification_are_checked(self):
        agg = '<script type="application/ld+json">{"@type": "Product", "offers": {"@type": "AggregateOffer", "lowPrice": "%s", "highPrice": "%s"}}</script>'
        spec = ('<script type="application/ld+json">{"@type": "SoftwareApplication", "offers": {"@type": "Offer", "price": "397", '
                '"priceSpecification": {"@type": "UnitPriceSpecification", "price": "%s"}}}</script>')
        problems = self.site({
            "good.html": page(head=agg % ("397", "995") + spec % "397"),
            "bad-agg.html": page(head=agg % ("299", "995")),
            "bad-spec.html": page(head=spec % "497"),
        })
        self.assertEqual(len(problems), 2)
        self.assertTrue(any("bad-agg.html" in p and "'299'" in p for p in problems))
        self.assertTrue(any("bad-spec.html" in p and "SoftwareApplication UnitPriceSpecification" in p for p in problems))

    def test_faq_question_with_toggle_arrow_is_reported(self):
        ld = ('<script type="application/ld+json">{"@type": "FAQPage", "mainEntity": ['
              '{"@type": "Question", "name": "%s", "acceptedAnswer": {"@type": "Answer", "text": "A"}}]}</script>')
        problems = self.site({"good.html": page(head=ld % "How much?"), "bad.html": page(head=ld % "How much? \u25bc")})
        self.assertEqual(len(problems), 1)
        self.assertIn("bad.html", problems[0])
        self.assertIn("toggle arrow", problems[0])

    def test_simulation_free_web_app_is_allowed(self):
        ld = '<script type="application/ld+json">{"@type": "WebApplication", "offers": {"@type": "Offer", "price": "0"}}</script>'
        self.assertEqual(self.site({"simulation.html": page(head=ld)}), [])

    def test_invalid_json_ld_is_reported(self):
        problems = self.site({"a.html": page(head='<script type="application/ld+json">{"a": }</script>')})
        self.assertEqual(len(problems), 1)
        self.assertIn("does not parse", problems[0])

    def test_retired_values_are_reported(self):
        problems = self.site({
            "a.html": page("<p>Setup is $999 today.</p><p>Don't see results? We refund your setup fee. No questions.</p>"),
            "llms.txt": "Pro costs $8,673/year.\nISA salary $67,500/year is fine.\n",
        })
        self.assertEqual(len(problems), 3)

    def test_old_isa_ratio_and_annual_range_are_reported(self):
        problems = self.site({
            "a.html": page("<p>4.5x the coverage at 12-18% of the cost.</p>"),
            "b.html": page("<p>Roughly $6,000-12,000 per year.</p><p>$6,000-$12,000 fully loaded.</p>"),
        })
        self.assertEqual(len(problems), 2)
        self.assertEqual(self.site({"a.html": page("<p>Pro and Elite cost roughly 14-20% of an ISA.</p>")}), [])

    def test_published_markdown_and_scripts_are_scanned(self):
        problems = self.site({
            "README.md": "The old $999 setup fee.\n",
            "scripts/a.js": "const note = 'Free trial available';\n",
            "_demo-api/README.md": "$999 is fine in an unpublished folder.\n",
        })
        self.assertEqual(len(problems), 2)
        self.assertTrue(any(p.startswith("README.md:1:") for p in problems))
        self.assertTrue(any(p.startswith("scripts/a.js:1:") for p in problems))

    def test_competitor_and_isa_figures_are_not_flagged(self):
        self.assertEqual(self.site({"a.html": page("<p>ISA: $67,500/year. GHL: $97/mo. A $9,999 tool.</p>")}), [])

    def test_demo_forms_must_match_each_other(self):
        problems = self.site({"es/index.html": page(FORM_ES.replace('<input name="email">', '<input name="email"><input name="plan">'))})
        self.assertEqual(len(problems), 1)
        self.assertIn("plan", problems[0])

    def test_demo_forms_must_fit_the_worker_allowlist(self):
        worker = (
            "const FIELDS = new Set(['first_name', 'email', 'leads_per_month', '_honey', 'language']);\n"
            "if (!['', '25-100'].includes(lead.leads_per_month) || x) return reply(400, 'fields');\n"
        )
        problems = self.site({"_demo-api/worker.mjs": worker})
        # Both forms offer "1-25", which this Worker would reject.
        self.assertEqual(len(problems), 2)
        self.assertTrue(all("would be rejected by the Worker" in p for p in problems))

    def test_worker_without_a_readable_volume_allowlist_fails_closed(self):
        worker = "const FIELDS = new Set(['first_name', 'email', 'leads_per_month', '_honey']);\n"
        problems = self.site({"_demo-api/worker.mjs": worker})
        self.assertEqual(len(problems), 1)
        self.assertIn("leads_per_month allowlist", problems[0])

    def test_underscore_folders_are_not_checked(self):
        self.assertEqual(self.site({"_tools/x.html": page('<img src="nope.png"> $999')}), [])

    def test_manifest_icon_must_match_declared_size(self):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (64).to_bytes(4, "big") + (32).to_bytes(4, "big")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "es").mkdir()
        (root / "index.html").write_text(page(FORM_EN))
        (root / "es/index.html").write_text(page(FORM_ES))
        (root / "icon.png").write_bytes(png)
        (root / "manifest.json").write_text('{"icons": [{"src": "/icon.png", "sizes": "192x192", "type": "image/png"}]}')
        problems = check(root)
        self.assertEqual(len(problems), 1)
        self.assertIn("64x32", problems[0])


if __name__ == "__main__":
    unittest.main()
