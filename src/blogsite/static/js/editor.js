/**
 * Live Markdown preview for the admin editor.
 * Uses the marked.js CDN for client-side rendering.
 * The authoritative render is always done server-side (Python-Markdown).
 */
(function () {
  "use strict";

  const MARKED_CDN =
    "https://cdn.jsdelivr.net/npm/marked@12/marked.min.js";

  function loadScript(src, cb) {
    var s = document.createElement("script");
    s.src = src;
    s.onload = cb;
    document.head.appendChild(s);
  }

  function initPreview() {
    var textarea = document.getElementById("content");
    var preview = document.getElementById("preview");
    if (!textarea || !preview) return;

    function update() {
      // marked is available after CDN load
      if (window.marked) {
        preview.innerHTML = window.marked.parse(textarea.value);
        if (window.hljs) {
          preview.querySelectorAll("pre code").forEach(function (block) {
            window.hljs.highlightElement(block);
          });
        }
      }
    }

    // Debounce so we don't re-render on every keypress
    var timer;
    textarea.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(update, 200);
    });

    loadScript(MARKED_CDN, function () {
      update(); // initial render
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPreview);
  } else {
    initPreview();
  }
})();
