const ORIGINS = new Set(['https://aisalespipeline.com', 'https://www.aisalespipeline.com']);
const FIELDS = new Set(['first_name', 'last_name', 'email', 'phone', 'leads_per_month', 'challenge', '_honey', 'language', 'cf-turnstile-response']);
const MAX_BYTES = 16384;

// Dependency injection is for offline tests only; the deployed entry always uses fetch.
export function createHandler(fetcher = fetch) {
  return async function handle(request, env) {
    const origin = request.headers.get('Origin');
    const headers = { 'Cache-Control': 'no-store', 'Vary': 'Origin', 'X-Content-Type-Options': 'nosniff' };
    if (ORIGINS.has(origin)) headers['Access-Control-Allow-Origin'] = origin;
    const reply = (status, code, extra = {}) => Response.json({ code }, { status, headers: { ...headers, ...extra } });
    if (new URL(request.url).pathname !== '/demo') return reply(404, 'not_found');
    if (!ORIGINS.has(origin)) return reply(403, 'origin');
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: { ...headers, 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type' } });
    if (request.method !== 'POST') return reply(405, 'method', { Allow: 'POST' });
    // No development bypass, public test secrets, or fail-open path in production.
    if (!env.TURNSTILE_SECRET_KEY || /^[123]x0+/.test(env.TURNSTILE_SECRET_KEY) || !env.RESEND_API_KEY || !env.MAIL_FROM || !env.MAIL_TO || !env.IP_LIMITER || !env.EMAIL_LIMITER) return reply(503, 'unavailable');
    const ip = request.headers.get('CF-Connecting-IP'); // Set by Cloudflare, never trust X-Forwarded-For.
    if (!ip) return reply(503, 'unavailable');
    if (request.headers.get('Content-Type')?.split(';')[0].trim() !== 'application/x-www-form-urlencoded') return reply(415, 'content_type');
    try {
      if (!(await env.IP_LIMITER.limit({ key: `demo:${ip}` })).success) return reply(429, 'rate_limit', { 'Retry-After': '60' });
      // Bound streamed input too: Content-Length alone is attacker-controlled.
      if (Number(request.headers.get('Content-Length')) > MAX_BYTES) return reply(413, 'too_large');
      const reader = request.body?.getReader();
      if (!reader) return reply(400, 'fields');
      const chunks = [];
      let size = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_BYTES) { await reader.cancel(); return reply(413, 'too_large'); }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      const form = new URLSearchParams(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
      for (const key of form.keys()) if (!FIELDS.has(key) || form.getAll(key).length !== 1) return reply(400, 'fields');
      if (form.get('_honey')) return reply(400, 'fields');
      const get = name => (form.get(name) || '').trim();
      const lead = Object.fromEntries(['first_name', 'last_name', 'email', 'phone', 'leads_per_month', 'challenge', 'language'].map(key => [key, get(key)]));
      if (!['en', 'es'].includes(lead.language)) return reply(400, 'fields');
      if (![lead.first_name, lead.last_name].every(v => v.length >= 1 && v.length <= 100 && !/[\r\n\x00-\x1f]/.test(v))) return reply(400, 'fields');
      if (lead.email.length > 254 || !/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(lead.email)) return reply(400, 'fields');
      if (lead.phone.length > 40 || !/^[+\d\s().-]+$/.test(lead.phone) || lead.phone.replace(/\D/g, '').length < 7 || lead.phone.replace(/\D/g, '').length > 20) return reply(400, 'fields');
      if (!['', '1-25', '25-100', '100-500', '500+'].includes(lead.leads_per_month) || lead.challenge.length > 4000) return reply(400, 'fields');
      const token = get('cf-turnstile-response');
      if (!token || token.length > 2048) return reply(400, 'verification');
      const verification = await fetcher('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ secret: env.TURNSTILE_SECRET_KEY, response: token, remoteip: ip }),
        signal: AbortSignal.timeout(8000)
      });
      if (!verification.ok) return reply(503, 'unavailable');
      const result = await verification.json();
      const age = Date.now() - Date.parse(result?.challenge_ts);
      if (result?.success !== true || result.hostname !== new URL(origin).hostname || result.action !== 'demo_request' || !Number.isFinite(age) || age < -60000 || age > 300000) return reply(400, 'verification');
      // Cloudflare consumes the token at Siteverify; replay/expiry fails before mail.
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(lead.email.toLowerCase()));
      const emailKey = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
      if (!(await env.EMAIL_LIMITER.limit({ key: emailKey })).success) return reply(429, 'rate_limit', { 'Retry-After': '60' });
      const sent = await fetcher('https://api.resend.com/emails', {
        method: 'POST', headers: { 'Authorization': `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          from: env.MAIL_FROM, to: [env.MAIL_TO], reply_to: lead.email,
          subject: lead.language === 'es' ? 'Nueva Solicitud de Demo - AI Sales Pipeline' : 'New AI Sales Pipeline Demo Request',
          text: `Name: ${lead.first_name} ${lead.last_name}\nEmail: ${lead.email}\nPhone: ${lead.phone}\nLeads per month: ${lead.leads_per_month || 'Not provided'}\nLanguage: ${lead.language}\n\nChallenge:\n${lead.challenge || 'Not provided'}`
        }), signal: AbortSignal.timeout(10000)
      });
      if (!sent.ok || !(await sent.json())?.id) return reply(503, 'delivery');
      return Response.json({ redirect: lead.language === 'es' ? 'https://aisalespipeline.com/es/gracias.html' : 'https://aisalespipeline.com/thanks.html' }, { headers });
    } catch {
      // Do not log PII, tokens, keys, or upstream bodies. Never claim delivery on error.
      return reply(503, 'unavailable');
    }
  };
}

export default { fetch: createHandler() };
