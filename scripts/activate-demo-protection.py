#!/usr/bin/env python3
"""Run only after deploying/configuring the worker. Produces a reviewable static diff."""
import argparse
import re
from pathlib import Path
from urllib.parse import urlparse

parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', required=True, help='Deployed HTTPS Worker URL ending in /demo')
parser.add_argument('--site-key', required=True, help='Production public Turnstile site key (not secret key)')
args = parser.parse_args()
url = urlparse(args.endpoint)
if url.scheme != 'https' or not url.hostname or url.path != '/demo' or url.query or url.fragment or url.username or url.password or not re.fullmatch(r'https://[a-zA-Z0-9.-]+(?::443)?/demo', args.endpoint):
    parser.error('Use the deployed HTTPS endpoint, with path /demo and no query or credentials.')
if not re.fullmatch(r'[a-zA-Z0-9_-]{10,100}', args.site_key) or re.match(r'[123]x0+', args.site_key):
    parser.error('Use a real production Turnstile site key, never a test key.')
root = Path(__file__).resolve().parent.parent
prepared = []
for file, lang in [('index.html', 'en'), ('es/index.html', 'es')]:
    path = root / file
    source = path.read_text()
    old = '<form action="https://formsubmit.co/jorgeramirez76@gmail.com" method="POST"'
    if source.count(old) != 1:
        parser.error(f'{file}: expected one unconverted form; refusing a partial conversion.')
    source = source.replace(old, f'<form action="{args.endpoint}" method="POST" data-demo-protected data-language="{lang}" data-sitekey="{args.site_key}"')
    source = re.sub(r'\s*<!-- (?:Formsubmit config|Keep FormSubmit[^>]*?) -->', '', source)
    source = re.sub(r'\s*<input type="hidden" name="_(?:subject|template|next)"[^>]*>', '', source)
    source = source.replace('<button type="submit"', '<button type="submit" disabled')
    note = 'Después de enviar, completa la verificación de seguridad para confirmar tu solicitud.' if lang == 'es' else 'After submitting, complete the security check to confirm your request.'
    replacement = f'<input type="hidden" name="language" value="{lang}"><div data-turnstile-widget></div><p role="status" aria-live="polite">'+ ('Verificando seguridad…' if lang == 'es' else 'Checking security…') + '</p><noscript>' + ('Activa JavaScript para solicitar una demo.' if lang == 'es' else 'Enable JavaScript to request a demo.') + '</noscript>'
    pattern = r'<p[^>]*>' + re.escape(note) + '</p>'
    source, count = re.subn(pattern, replacement, source)
    if count != 1: parser.error(f'{file}: expected the CAPTCHA notice.')
    source = source.replace('</body>', '<script src="/scripts/demo-turnstile.js" defer></script>\n</body>')
    prepared.append((path, source))
for path, source in prepared:
    path.write_text(source)
    print(f'Prepared {path.name} for {args.endpoint}; review and deploy after server validation.')
