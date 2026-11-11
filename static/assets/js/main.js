/* ps.wawa — общий скрипт. Контент страниц в JS не рендерится: только меню, липкая кнопка, анимации и аналитика. */
(function () {
  'use strict';
  var doc = document.documentElement;
  var lang = doc.lang || 'ru';

  /* --- Мобильное меню --- */
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('mobile-nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) { nav.classList.remove('is-open'); btn.setAttribute('aria-expanded', 'false'); }
    });
  }

  /* --- Липкая кнопка: появляется, когда главная кнопка hero ушла из экрана --- */
  var sticky = document.querySelector('.sticky-cta');
  var heroCta = document.querySelector('[data-hero-cta]');
  if (sticky) {
    if (heroCta && 'IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        sticky.classList.toggle('is-visible', !entries[0].isIntersecting);
      }).observe(heroCta);
    } else {
      sticky.classList.add('is-visible');
    }
  }

  /* --- Появление блоков при скролле --- */
  var reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('is-in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add('is-in'); });
  }

  /* --- GA4: событие click_instagram для каждой ссылки в Instagram ---
     item: ps5 / ps5pro / ps4xbox / vr2 / hookah / general (из data-item), lang — из <html lang> */
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[data-ig]');
    if (!a) return;
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'click_instagram', {
        item: a.getAttribute('data-item') || 'general',
        lang: lang,
        placement: a.getAttribute('data-place') || '',
        transport_type: 'beacon'
      });
    }
  });
})();
