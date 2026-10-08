# Demo request abuse protection

## Status

The immediate mitigation is live on GitHub Pages: PR #4 restores FormSubmit's default hosted CAPTCHA and adds its supported `_honey` field to both English and Spanish forms. Existing recipient, required inputs, and success pages are unchanged.

**This Worker and the Turnstile client are prepared, not activated or deployed.** The live forms still use FormSubmit. No real Cloudflare/Resend keys are included or assumed, and no email was sent during testing.

FormSubmit accepts `_captcha=false` in the caller's payload. Removing it from our HTML helps normal form traffic but cannot close direct submissions to that provider endpoint. Its honeypot can also be omitted by a bot. CORS and Origin checks alone are not authentication; direct clients can forge Origin.

## Prepared enforcement

The Worker accepts only POST `/demo` from the two exact website origins. Before delivery it enforces a 16 KiB streamed body cap, a field allowlist, duplicate-field rejection, contact-field validation, a honeypot, and Cloudflare's Siteverify response including hostname, action and timestamp. Missing/invalid/replayed tokens never reach the email adapter. Verification or configuration outages fail closed. Public Turnstile test secrets are rejected.

Cloudflare rate-limit bindings limit attempts to 20 per IP per minute, with up to 3 verified submissions per email per minute. These are per-location, eventually consistent abuse limits, not a strict global quota. The IP limit is deliberately generous for shared office connections. Cloudflare supplies the trusted IP header; no caller-supplied forwarding header is used. The email key is hashed, and application code logs no contact details or tokens.

Mail goes directly through Resend to a fixed server-configured recipient, with plain-text content and the prospect's email as Reply-To. Neither recipient, subject, sender, redirect nor verification policy can be supplied by the client. No auto-response is sent to prospects. The client disables duplicate submissions and resets consumed tokens after failures while preserving entered details. A mail-service timeout has an ambiguous delivery outcome, reported as unconfirmed to the visitor; there is no automatic mail retry.

## Activation (requires account access/configuration)

1. Connect the intended Cloudflare account, with Worker deployment and Turnstile widget access. Create a **Managed** Turnstile widget allowing only `aisalespipeline.com` and `www.aisalespipeline.com`. The public site key goes in HTML; the secret key only in Worker secrets. No DNS migration is required when the Worker uses its `workers.dev` URL.
2. Connect a Resend account with a verified sender. Use a sending-only key restricted to that domain. If another transactional email service is already authorized, replace only the mail adapter and its tests instead of opening another account.
3. From this directory, set secrets securely with `npx wrangler@4.148.0 secret put TURNSTILE_SECRET_KEY`, `RESEND_API_KEY`, `MAIL_FROM`, and `MAIL_TO`. Set `MAIL_TO` to the existing intended demo inbox. Never put secrets in HTML, Git, shell arguments, or this README. Ignore `.dev.vars` and local environment files.
4. Confirm both rate-limit namespace IDs in `wrangler.toml` are unused in that Cloudflare account. Run `npx wrangler@4.148.0 deploy --dry-run`, then deploy the configured Worker. Verify missing/invalid tokens are rejected on the deployed `/demo` endpoint without sending mail. Perform an authorized positive delivery check using a controlled test recipient before cutover; production credentials and real challenge verification have **not** yet been tested.
5. From the repository root run `python3 scripts/activate-demo-protection.py --endpoint https://YOUR-WORKER.workers.dev/demo --site-key YOUR_PUBLIC_SITE_KEY`. This edits both forms together, removes FormSubmit settings, adds the correct language, includes the Turnstile client, and disables submission until verified. Review the resulting two-file diff. Test both languages, expired challenges, blocked scripts and provider failures before deploying it through a PR to `main` (GitHub Pages).
6. Retire the **old FormSubmit intake at the provider** after confirming the new flow. Removing its URL from HTML does not revoke it. Check for other sites that share that mailbox before disabling anything: a mailbox-wide unsubscribe could break unrelated sites. Obtain form-specific provider disablement if possible; otherwise agree on a scoped replacement/filtering plan. Do not label protection complete while forged requests to the old route can still produce demo notifications.
7. Update the site's privacy disclosure to describe the configured verification and email processors at cutover. Confirm the normal confirmation pages are reached only after accepted delivery.

Do not run activation with placeholder/test keys or point live forms at an unconfigured endpoint. Before cutover, rollback means leaving the current live FormSubmit mitigation intact. After cutover, prefer fixing the protected endpoint; restoring FormSubmit also restores the known bypass.

## Validation

From the repository root:

```sh
node --test tests/*.test.mjs
```

The tests use injected, in-memory Cloudflare and mail responses, never the network. They cover legitimate English/Spanish requests, missing/forged/expired/replayed tokens, wrong action/hostname, direct calls, `_captcha=false`, recipient/redirect overrides, malformed and oversized input, both rate limits, missing credentials, provider failures, duplicate submissions, client recovery, and blocked verification scripts. Replay tests exercise the response to Siteverify's single-use semantics; they are not a substitute for a real integration test.

Wrangler 4.148.0 successfully bundled the Worker in a deployment dry run with both rate-limit bindings. `wrangler whoami` confirms this environment is not authenticated to Cloudflare.

The activation script has also been run against temporary copies of both pages: both produce the protected markup, and a repeated conversion fails without changing either file. The live source was checked after deployment: both pages have no CAPTCHA opt-out and include the honeypot. The live hosted CAPTCHA and actual inbox delivery were not exercised because doing so would send an external message.

Reference documentation:

- https://formsubmit.co/documentation
- https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
- https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/
- https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- https://resend.com/docs/api-reference/emails/send-email
