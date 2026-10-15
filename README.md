# ai-sales-pipeline
AI-powered sales CRM for SMS, email, voice calls, marketing automation, and follow-up workflows.

## Before changing the live site

GitHub Pages publishes `main` as soon as it changes, so make changes on a branch and open a pull request.

The **Site check** GitHub Action runs `python3 _tools/check_site.py` on every pull request and push. You can run it yourself first; it needs only Python 3. It checks that:

- every internal link, image, sitemap entry and manifest icon points at a real file;
- every structured-data (JSON-LD) block parses, and every plan price in it is $397, $695 or $995;
- retired prices and old wording (for example the old $999 setup fee or a "no questions" refund) do not come back;
- the English and Spanish demo forms send the same fields.

**When a price changes:** update every page that shows it, then add the *old* value to `RETIRED` in `_tools/check_site.py` in the same pull request, so a missed page fails the check instead of going live.

Folders whose names start with `_` (like `_tools/`) are not published by GitHub Pages.
