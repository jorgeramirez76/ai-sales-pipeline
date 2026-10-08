import test from 'node:test';
import assert from 'node:assert/strict';
import { createHandler } from '../_demo-api/worker.mjs';

const valid = { first_name: 'Ada', last_name: 'Test', email: 'ada@example.invalid', phone: '+1 202 555 0100', leads_per_month: '25-100', challenge: 'Following up', language: 'en', _honey: '', 'cf-turnstile-response': 'fresh-token' };
function fixture(options = {}) {
  const calls = [];
  const used = new Set();
  const env = {
    TURNSTILE_SECRET_KEY: 'offline-secret', RESEND_API_KEY: 'offline-mail-key', MAIL_FROM: 'Demo <sender@example.invalid>', MAIL_TO: 'inbox@example.invalid',
    IP_LIMITER: { limit: async () => ({ success: options.ipAllowed !== false }) },
    EMAIL_LIMITER: { limit: async () => ({ success: options.emailAllowed !== false }) }
  };
  const handle = createHandler(async (url, init) => {
    const payload = JSON.parse(init.body);
    calls.push({ url, payload });
    if (url.includes('siteverify')) {
      if (options.verifyThrows) throw new Error('network');
      const success = !used.has(payload.response) && options.verified !== false;
      used.add(payload.response);
      return Response.json({ success, hostname: 'aisalespipeline.com', action: 'demo_request', challenge_ts: new Date().toISOString(), ...options.verification }, { status: options.verifyStatus || 200 });
    }
    assert.equal(url, 'https://api.resend.com/emails');
    return Response.json(options.mailBody || { id: 'offline-mail-id' }, { status: options.mailStatus || 200 });
  });
  function request(fields = {}, { origin = 'https://aisalespipeline.com', method = 'POST', type = 'application/x-www-form-urlencoded', raw, ip = '192.0.2.1', path = '/demo' } = {}) {
    const headers = { 'Content-Type': type };
    if (origin) headers.Origin = origin;
    if (ip) headers['CF-Connecting-IP'] = ip;
    return new Request(`https://demo.example.invalid${path}`, { method, headers, ...(!['GET', 'OPTIONS'].includes(method) && { body: raw ?? new URLSearchParams({ ...valid, ...fields }) }) });
  }
  return { handle, request, env, calls, mail: () => calls.filter(c => c.url.includes('resend')) };
}

for (const language of ['en', 'es']) test(`legitimate ${language} request verifies before fixed-recipient delivery`, async () => {
  const f = fixture();
  const response = await f.handle(f.request({ language }), f.env);
  assert.equal(response.status, 200);
  assert.equal((await response.json()).redirect, language === 'es' ? 'https://aisalespipeline.com/es/gracias.html' : 'https://aisalespipeline.com/thanks.html');
  assert.equal(f.calls.length, 2);
  assert.match(f.calls[0].url, /siteverify/);
  assert.deepEqual(f.mail()[0].payload.to, ['inbox@example.invalid']);
  assert.equal(f.mail()[0].payload.reply_to, valid.email);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), 'https://aisalespipeline.com');
});

const rejected = [
  ['missing token', { 'cf-turnstile-response': '' }, {}, {}, 400],
  ['oversized token', { 'cf-turnstile-response': 'x'.repeat(2049) }, {}, {}, 400],
  ['forged token', {}, {}, { verified: false }, 400],
  ['expired token', {}, {}, { verification: { challenge_ts: new Date(Date.now() - 301000).toISOString() } }, 400],
  ['missing timestamp', {}, {}, { verification: { challenge_ts: null } }, 400],
  ['future timestamp', {}, {}, { verification: { challenge_ts: new Date(Date.now() + 120000).toISOString() } }, 400],
  ['wrong hostname', {}, {}, { verification: { hostname: 'attacker.invalid' } }, 400],
  ['wrong action', {}, {}, { verification: { action: 'other' } }, 400],
  ['verification outage', {}, {}, { verifyThrows: true }, 503],
  ['verification HTTP error', {}, {}, { verifyStatus: 503 }, 503],
  ['honeypot filled', { _honey: 'spam' }, {}, {}, 400],
  ['CAPTCHA bypass flag', { _captcha: 'false' }, {}, {}, 400],
  ['recipient override', { to: 'other@example.invalid' }, {}, {}, 400],
  ['redirect override', { _next: 'https://attacker.invalid' }, {}, {}, 400],
  ['missing name', { first_name: '' }, {}, {}, 400],
  ['invalid email', { email: 'not-an-email' }, {}, {}, 400],
  ['email header injection', { email: 'a@example.invalid\r\nBcc:x@example.invalid' }, {}, {}, 400],
  ['invalid phone', { phone: 'bad' }, {}, {}, 400],
  ['invalid range', { leads_per_month: '1000000' }, {}, {}, 400],
  ['long message', { challenge: 'x'.repeat(4001) }, {}, {}, 400],
  ['invalid language', { language: 'xx' }, {}, {}, 400],
  ['missing Origin / direct endpoint', {}, { origin: null }, {}, 403],
  ['foreign Origin', {}, { origin: 'https://attacker.invalid' }, {}, 403],
  ['lookalike Origin', {}, { origin: 'https://aisalespipeline.com.attacker.invalid' }, {}, 403],
  ['GET bypass', {}, { method: 'GET' }, {}, 405],
  ['JSON bypass', {}, { type: 'application/json', raw: JSON.stringify(valid) }, {}, 415],
  ['duplicate token fields', {}, { raw: new URLSearchParams(valid).toString() + '&cf-turnstile-response=second' }, {}, 400],
  ['oversized streamed body', {}, { raw: 'x='.padEnd(17000, 'a') }, {}, 413],
  ['IP rate limit', {}, {}, { ipAllowed: false }, 429],
  ['email rate limit', {}, {}, { emailAllowed: false }, 429],
  ['missing edge IP', {}, { ip: null }, {}, 503],
  ['unknown route', {}, { path: '/ajax' }, {}, 404]
];
for (const [name, fields, request, options, status] of rejected) test(`${name} never sends mail`, async () => {
  const f = fixture(options);
  const response = await f.handle(f.request(fields, request), f.env);
  assert.equal(response.status, status);
  assert.equal(f.mail().length, 0);
});

test('replay is rejected when Siteverify reports consumed token', async () => {
  const f = fixture();
  assert.equal((await f.handle(f.request(), f.env)).status, 200);
  assert.equal((await f.handle(f.request(), f.env)).status, 400);
  assert.equal(f.mail().length, 1);
});
for (const key of ['TURNSTILE_SECRET_KEY', 'RESEND_API_KEY', 'MAIL_FROM', 'MAIL_TO', 'IP_LIMITER', 'EMAIL_LIMITER']) test(`missing ${key} fails closed`, async () => {
  const f = fixture(); delete f.env[key];
  assert.equal((await f.handle(f.request(), f.env)).status, 503);
  assert.equal(f.calls.length, 0);
});
test('public Turnstile test secrets cannot enable production delivery', async () => {
  const f = fixture(); f.env.TURNSTILE_SECRET_KEY = '1x0000000000000000000000000000000AA';
  assert.equal((await f.handle(f.request(), f.env)).status, 503);
  assert.equal(f.calls.length, 0);
});
for (const options of [{ mailStatus: 500 }, { mailBody: {} }]) test('mail provider failure is not a success', async () => {
  const f = fixture(options);
  const response = await f.handle(f.request(), f.env);
  assert.equal(response.status, 503);
  assert.equal((await response.json()).code, 'delivery');
});
test('www hostname is accepted only when verified for that origin', async () => {
  const f = fixture({ verification: { hostname: 'www.aisalespipeline.com' } });
  assert.equal((await f.handle(f.request({}, { origin: 'https://www.aisalespipeline.com' }), f.env)).status, 200);
});
test('approved preflight has no side effects', async () => {
  const f = fixture();
  assert.equal((await f.handle(f.request({}, { method: 'OPTIONS' }), f.env)).status, 204);
  assert.equal(f.calls.length, 0);
});
