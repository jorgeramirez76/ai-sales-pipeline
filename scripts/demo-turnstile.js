(() => {
  const form = document.querySelector('form[data-demo-protected]');
  if (!form) return;
  const es = form.dataset.language === 'es';
  const button = form.querySelector('button[type="submit"]');
  const status = form.querySelector('[role="status"]');
  const widget = form.querySelector('[data-turnstile-widget]');
  let ready = false;
  let sending = false;
  let widgetId;
  let deliveryError = "";
  const copy = es ? {
    loading: 'Verificando seguridad…', ready: 'Verificación completada.',
    error: 'No se pudo verificar. Recarga la página e inténtalo de nuevo.',
    expired: 'La verificación caducó. Espera a que se renueve.',
    sending: 'Enviando tu solicitud…', failed: 'No se pudo confirmar el envío. Tus datos siguen aquí. Inténtalo de nuevo.',
    rate: 'Demasiados intentos. Espera un minuto antes de volver a intentar.'
  } : {
    loading: 'Checking security…', ready: 'Security check complete.',
    error: 'Security verification could not load. Reload the page and try again.',
    expired: 'Security check expired. Waiting for a fresh check.',
    sending: 'Sending your request…', failed: 'We could not confirm delivery. Your details are still here. Please try again.',
    rate: 'Too many attempts. Please wait a minute before trying again.'
  };
  function state(verified, message) {
    ready = verified;
    button.disabled = sending || !ready;
    status.textContent = message;
  }
  state(false, copy.loading);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (!ready || sending || !form.reportValidity()) return;
    sending = true;
    deliveryError = "";
    state(true, copy.sending);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new URLSearchParams(new FormData(form)),
        credentials: 'omit', signal: AbortSignal.timeout(25000)
      });
      const result = await response.json();
      const destination = es ? 'https://aisalespipeline.com/es/gracias.html' : 'https://aisalespipeline.com/thanks.html';
      if (!response.ok || result.redirect !== destination) throw new Error(response.status === 429 ? 'rate' : 'delivery');
      window.location.assign(destination);
    } catch (error) {
      sending = false;
      deliveryError = error.message === 'rate' ? copy.rate : copy.failed;
      state(false, deliveryError);
      // Siteverify consumes tokens, including when later delivery fails.
      window.turnstile?.reset(widgetId);
    }
  });
  const script = document.createElement('script');
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  script.async = true;
  script.onerror = () => state(false, copy.error);
  script.onload = () => {
    try {
      widgetId = window.turnstile.render(widget, {
        sitekey: form.dataset.sitekey, action: 'demo_request', language: es ? 'es' : 'en', theme: 'dark', size: 'flexible',
        callback: () => state(true, deliveryError || copy.ready),
        'expired-callback': () => state(false, copy.expired),
        'error-callback': () => { state(false, copy.error); return true; },
        'timeout-callback': () => state(false, copy.error)
      });
    } catch { state(false, copy.error); }
  };
  document.head.appendChild(script);
})();
