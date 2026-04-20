/**
 * AutoSEO Monitoring Snippet (~3KB minified)
 * Embed: <script src="https://cdn.autoseo.com/snippet.js" data-token="SITE_TOKEN" async></script>
 * Collects: page meta, Core Web Vitals (LCP, CLS, TTFB), SPA navigation support
 */
(function () {
  'use strict';

  var token = document.currentScript && document.currentScript.getAttribute('data-token');
  if (!token) { console.warn('[AutoSEO] Missing data-token attribute'); return; }

  var endpoint = 'https://api.autoseo.com/snippet/collect';
  var sent = new Set();

  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? el.getAttribute('content') || null : null;
  }

  function getOg(prop) {
    var el = document.querySelector('meta[property="og:' + prop + '"]');
    return el ? el.getAttribute('content') || null : null;
  }

  function getSchema() {
    return Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
      .map(function (s) { return s.textContent; })
      .filter(Boolean)
      .join('\n');
  }

  function collect() {
    var url = window.location.href;
    if (sent.has(url)) return;
    sent.add(url);

    var data = {
      token: token,
      url: url,
      title: document.title || null,
      meta_description: getMeta('description'),
      canonical: (document.querySelector('link[rel="canonical"]') || {}).href || null,
      h1: (document.querySelector('h1') || {}).innerText || null,
      schema: getSchema() || null,
      og_title: getOg('title'),
      og_image: getOg('image'),
      viewport_width: window.innerWidth,
      user_agent: navigator.userAgent,
    };

    /* Core Web Vitals via PerformanceObserver */
    if (typeof PerformanceObserver !== 'undefined') {
      try {
        new PerformanceObserver(function (list) {
          var entries = list.getEntries();
          if (entries.length) {
            data.lcp = Math.round(entries[entries.length - 1].startTime);
          }
        }).observe({ type: 'largest-contentful-paint', buffered: true });
      } catch (e) { /* noop */ }

      try {
        var clsScore = 0;
        new PerformanceObserver(function (list) {
          list.getEntries().forEach(function (entry) {
            if (!entry.hadRecentInput) clsScore += entry.value;
          });
          data.cls = Math.round(clsScore * 1000) / 1000;
        }).observe({ type: 'layout-shift', buffered: true });
      } catch (e) { /* noop */ }
    }

    /* TTFB from Navigation Timing */
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav) data.ttfb = Math.round(nav.responseStart - nav.requestStart);
    } catch (e) { /* noop */ }

    /* Send beacon after short delay to capture vitals */
    setTimeout(function () {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(endpoint, JSON.stringify(data));
      } else {
        /* Fallback XHR */
        try {
          var xhr = new XMLHttpRequest();
          xhr.open('POST', endpoint, true);
          xhr.setRequestHeader('Content-Type', 'application/json');
          xhr.send(JSON.stringify(data));
        } catch (e) { /* noop */ }
      }
    }, 2000);
  }

  /* Initial collection */
  if (document.readyState === 'complete') {
    collect();
  } else {
    window.addEventListener('load', collect);
  }

  /* SPA navigation support — React Router, Next.js, Vue Router */
  var lastUrl = location.href;
  new MutationObserver(function () {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      sent.delete(location.href);
      setTimeout(collect, 1200);
    }
  }).observe(document.body || document.documentElement, { childList: true, subtree: true });

})();
