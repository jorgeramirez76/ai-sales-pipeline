import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const source = readFileSync(new URL('../scripts/demo-turnstile.js', import.meta.url), 'utf8');
function fixture(response = Response.json({ redirect: 'https://aisalespipeline.com/thanks.html' })) {
  const button = {}, status = {}, widget = {};
  const state = { resets: 0, posts: [], navigation: [] };
  const form = {
    dataset: { language: 'en', sitekey: 'public-site-key' }, action: 'https://endpoint.example.invalid/demo',
    querySelector: selector => selector.startsWith('button') ? button : selector.includes('status') ? status : widget,
    reportValidity: () => true, addEventListener: (name, fn) => { state.submit = fn; }
  };
  const window = { location: { assign: url => state.navigation.push(url) }, turnstile: {
    render: (element, options) => { state.options = options; return 'widget-1'; }, reset: () => { state.resets++; }
  } };
  const document = { querySelector: () => form, createElement: () => ({}), head: { appendChild: script => { state.script = script; } } };
  vm.runInNewContext(source, { document, window, URLSearchParams, AbortSignal,
    FormData: class { *[Symbol.iterator]() { yield ['first_name', 'Ada']; yield ['cf-turnstile-response', 'fresh-token']; } },
    fetch: async (url, init) => { state.posts.push({ url, init }); if (response instanceof Error) throw response; return response; }
  });
  return { state, form, button, status, submit: () => state.submit({ preventDefault() {} }) };
}
test('client stays blocked until verified and submits exactly once', async () => {
  const f = fixture();
  assert.equal(f.button.disabled, true);
  await f.submit(); assert.equal(f.state.posts.length, 0);
  f.state.script.onload(); f.state.options.callback();
  assert.equal(f.button.disabled, false);
  await f.submit(); await f.submit();
  assert.equal(f.state.posts.length, 1);
  assert.equal(f.state.posts[0].init.body.get('cf-turnstile-response'), 'fresh-token');
  assert.deepEqual(f.state.navigation, ['https://aisalespipeline.com/thanks.html']);
});
test('blocked script keeps form disabled with recovery message', () => {
  const f = fixture(); f.state.script.onerror();
  assert.equal(f.button.disabled, true); assert.match(f.status.textContent, /Reload/);
});
for (const callback of ['expired-callback', 'error-callback', 'timeout-callback']) test(`${callback} disables submission`, async () => {
  const f = fixture(); f.state.script.onload(); f.state.options.callback(); f.state.options[callback]();
  await f.submit(); assert.equal(f.state.posts.length, 0); assert.equal(f.button.disabled, true);
});
for (const response of [new Error('network'), Response.json({ code: 'rate_limit' }, { status: 429 }), Response.json({ code: 'delivery' }, { status: 503 }), Response.json({ redirect: 'https://attacker.invalid' })]) test('failure resets consumed token, preserves form, and avoids success redirect', async () => {
  const f = fixture(response); f.state.script.onload(); f.state.options.callback(); await f.submit();
  assert.equal(f.state.resets, 1); assert.equal(f.button.disabled, true); assert.equal(f.state.navigation.length, 0);
  assert.match(f.status.textContent, /minute|details are still here/);
  f.state.options.callback();
  assert.equal(f.button.disabled, false);
  assert.match(f.status.textContent, /minute|details are still here/);
});
