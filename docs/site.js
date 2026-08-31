(() => {
  'use strict';

  const clock = document.querySelector('#siteClock');
  const year = document.querySelector('#siteYear');
  const ribbon = document.querySelector('#ribbonStatus');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function updateClock() {
    if (!clock) return;
    const value = new Date().toLocaleTimeString('de-DE', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC'
    });
    clock.textContent = `${value} UTC`;
  }

  updateClock();
  window.setInterval(updateClock, 1000);
  if (year) year.textContent = String(new Date().getUTCFullYear());

  if (ribbon && !reducedMotion) {
    const states = ['SOT ONLINE', 'AUDIT READY', 'SAFE MODE ON'];
    let index = 0;
    window.setInterval(() => {
      index = (index + 1) % states.length;
      ribbon.textContent = states[index];
    }, 3800);
  }

  const revealItems = [...document.querySelectorAll('.reveal')];
  if (reducedMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach((item) => item.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver((entries, currentObserver) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      currentObserver.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: .08 });
  revealItems.forEach((item) => observer.observe(item));
})();
