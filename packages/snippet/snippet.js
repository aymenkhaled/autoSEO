/**
 * AutoSEO Monitoring Snippet (~3.5KB minified)
 * Embed: <script src="https://cdn.autoseo.com/snippet.js" data-token="SITE_TOKEN" async></script>
 *
 * Collects:
 *   - Page meta (title, description, canonical, h1, schema, og:*)
 *   - Core Web Vitals: LCP, CLS, INP, TTFB, FCP
 *   - SPA navigation (History API + MutationObserver)
 *
 * Phase 2 hardening (from gap analysis):
 *   - Gap 16: collects INP (Core Web Vital since 2024)
 *   - Gap 17: client-side sampling via data-sample (default 100%)
 *   - Gap 18: respects navigator.doNotTrack
 *   - Gap 20: waits for DOM update before re-collecting on SPA nav
 */
(function () {
  'use strict';

  var script = document.currentScript;
  var token = script && script.getAttribute('data-token');
  if (!token) { console.warn('[AutoSEO] Missing data-token attribute'); return; }

  // Gap 18 — respect Do Not Track
  if (navigator.doNotTrack === '1' || window.doNotTrack === '1') return;

  // Gap 17 — configurable sampling (default 100%)
  var sampleRate = parseFloat((script && script.getAttribute('data-sample')) || '1');
  if (Math.random() > sampleRate) return;

  var endpoint = (script && script.getAttribute('data-endpoint')) ||
                 'https://api.autoseo.com/snippet/collect';
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

  function send(data) {
    try {
      var body = JSON.stringify(data);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(endpoint, body);
      } else {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', endpoint, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.send(body);
      }
    } catch (e) { /* noop */ }
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

    if (typeof PerformanceObserver !== 'undefined') {
      // LCP
      try {
        new PerformanceObserver(function (list) {
          var entries = list.getEntries();
          if (entries.length) {
            data.lcp = Math.round(entries[entries.length - 1].startTime);
          }
        }).observe({ type: 'largest-contentful-paint', buffered: true });
      } catch (e) {}

      // CLS
      try {
        var clsScore = 0;
        new PerformanceObserver(function (list) {
          list.getEntries().forEach(function (entry) {
            if (!entry.hadRecentInput) clsScore += entry.value;
          });
          data.cls = Math.round(clsScore * 1000) / 1000;
        }).observe({ type: 'layout-shift', buffered: true });
      } catch (e) {}

      // FCP
      try {
        new PerformanceObserver(function (list) {
          list.getEntries().forEach(function (entry) {
            if (entry.name === 'first-contentful-paint') {
              data.fcp = Math.round(entry.startTime);
            }
          });
        }).observe({ type: 'paint', buffered: true });
      } catch (e) {}

      // INP — Gap 16. Track the worst interaction's processing time.
      try {
        var worstInp = 0;
        new PerformanceObserver(function (list) {
          list.getEntries().forEach(function (entry) {
            if (entry.duration > worstInp) {
              worstInp = entry.duration;
              data.inp = Math.round(worstInp);
            }
          });
        }).observe({ type: 'event', buffered: true, durationThreshold: 16 });
      } catch (e) {}
    }

    // TTFB from Navigation Timing
    try {
      var nav = performance.getEntriesByType('navigation')[0];
      if (nav) data.ttfb = Math.round(nav.responseStart - nav.requestStart);
    } catch (e) {}

    // Send slightly later so observers can capture vitals
    setTimeout(function () { send(data); }, 2500);
  }

  // Initial collection
  if (document.readyState === 'complete') {
    collect();
  } else {
    window.addEventListener('load', collect);
  }

  // Send a final snapshot on unload (captures CLS up to the moment user leaves)
  window.addEventListener('pagehide', function () {
    if (sent.size) {
      // Re-snapshot the current URL
      sent.delete(window.location.href);
      collect();
    }
  });

  // SPA navigation — Gap 20: wait for DOM update before re-collecting
  var lastUrl = location.href;
  function onMaybeNav() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      sent.delete(location.href);
      setTimeout(collect, 1500);  // Give SPA router time to render
    }
  }
  try {
    new MutationObserver(onMaybeNav).observe(
      document.body || document.documentElement,
      { childList: true, subtree: true }
    );
  } catch (e) {}

  // Patch History API for instant SPA detection
  ['pushState', 'replaceState'].forEach(function (m) {
    var orig = history[m];
    history[m] = function () {
      var ret = orig.apply(this, arguments);
      setTimeout(onMaybeNav, 100);
      return ret;
    };
  });
  window.addEventListener('popstate', function () { setTimeout(onMaybeNav, 100); });

})();
