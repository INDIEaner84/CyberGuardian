/* Applies the stored CyberGuardian style world before the first paint, so a
   themed cockpit never flashes the default look. Keep the list in sync with
   THEME_IDS in app.js (tests/test_themes.py checks this). */
(function () {
  'use strict';
  var themes = ['enterprise', 'akira', 'cyberpunk', 'agentur', 'uboot'];
  try {
    var stored = window.localStorage.getItem('cyberguardian.theme');
    if (themes.indexOf(stored) !== -1) document.documentElement.setAttribute('data-theme', stored);
  } catch (error) {
    /* Storage blocked: keep the default Nightwatch look. */
  }
}());
